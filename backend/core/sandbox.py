import asyncio
import tempfile
import os
import shutil
import sys
from pathlib import Path

# Repo root = two levels up from backend/core/sandbox.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_PYTEST_IMAGE = "codeagentpro-pytest-sandbox:py3.11-slim"
_PYTEST_IMAGE_READY = None  # tri-state cache: None = unchecked this process

_DOCKER_AVAILABLE = None
FORCE_LOCAL_SANDBOX = os.getenv("FORCE_LOCAL_SANDBOX", "false").lower() == "true"
# Local fallback runs generated code directly on the host with NO isolation
# (no container, no --network none, no memory cap). It must be opted into
# explicitly. Forcing local mode implies consent to it.
ALLOW_LOCAL_SANDBOX = os.getenv("ALLOW_LOCAL_SANDBOX", "false").lower() == "true"


class LocalSandboxDisabledError(RuntimeError):
    """Docker is unavailable and unsandboxed local execution has not been enabled."""


_LOCAL_DISABLED_MSG = (
    "No isolated execution sandbox is available: Docker is not running and "
    "local fallback execution is disabled. Start Docker Desktop, or set "
    "ALLOW_LOCAL_SANDBOX=true to run generated code directly on this host "
    "(NOT isolated — local development only)."
)


def _local_allowed() -> bool:
    return ALLOW_LOCAL_SANDBOX or FORCE_LOCAL_SANDBOX


async def check_docker() -> bool:
    global _DOCKER_AVAILABLE
    if _DOCKER_AVAILABLE is not None:
        return _DOCKER_AVAILABLE

    if not shutil.which("docker"):
        _DOCKER_AVAILABLE = False
        return False

    try:
        import subprocess
        res = await asyncio.to_thread(
            subprocess.run,
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2
        )
        _DOCKER_AVAILABLE = (res.returncode == 0)
    except Exception:
        _DOCKER_AVAILABLE = False

    return _DOCKER_AVAILABLE


async def _ensure_pytest_image() -> bool:
    """Build (once, lazily) a local image with pytest pre-installed.

    The Python test-run container executes with --network none for
    isolation, so pytest can't be `pip install`-ed at container start —
    it has to already be baked into the image. `docker build` itself runs
    on the host daemon (which does have network access) the first time
    this image is needed; after that it's a fast local cache hit.
    """
    global _PYTEST_IMAGE_READY
    if _PYTEST_IMAGE_READY is not None:
        return _PYTEST_IMAGE_READY

    import subprocess

    try:
        inspect_res = await asyncio.to_thread(
            subprocess.run,
            ["docker", "image", "inspect", _PYTEST_IMAGE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        if inspect_res.returncode == 0:
            _PYTEST_IMAGE_READY = True
            return True
    except Exception:
        pass

    dockerfile = _PROJECT_ROOT / "docker" / "Dockerfile.pytest-sandbox"
    try:
        build_res = await asyncio.to_thread(
            subprocess.run,
            ["docker", "build", "-f", str(dockerfile), "-t", _PYTEST_IMAGE, str(dockerfile.parent)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        _PYTEST_IMAGE_READY = (build_res.returncode == 0)
    except Exception:
        _PYTEST_IMAGE_READY = False

    return _PYTEST_IMAGE_READY


class ExecutionSandbox:
    """
    Runs code inside a Docker container or local fallback sandbox.
    Supports Python, JavaScript, and C++.
    """

    DOCKER_IMAGE = "python:3.11-slim"
    TIMEOUT_SECONDS = 30

    # Non-root uid:gid ("nobody") used for every container that doesn't need
    # to install packages at runtime. Numeric IDs work without an /etc/passwd
    # entry, so this holds across all three base images.
    _NOBODY_UID = "65534:65534"

    @staticmethod
    def _safety_flags(non_root: bool = True) -> list:
        """Common hardening flags applied to every `docker run` invocation:
        fork-bomb protection, a CPU cap, no privilege escalation, and every
        Linux capability dropped. `non_root` is False only for the one path
        (Python test runs) that does `pip install` at container start and
        therefore needs root to write into site-packages.
        """
        flags = [
            "--pids-limit", "128",
            "--cpus", "1",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
        ]
        if non_root:
            flags += ["--user", ExecutionSandbox._NOBODY_UID]
        return flags

    async def run_code(self, code: str, language: str = "Python") -> dict:
        use_docker = (not FORCE_LOCAL_SANDBOX) and (not ALLOW_LOCAL_SANDBOX) and (await check_docker())
        lang = language.lower()

        ext = ".py"
        if "javascript" in lang or "js" in lang:
            ext = ".js"
        elif "c++" in lang or "cpp" in lang:
            ext = ".cpp"

        filename = f"solution{ext}"

        with tempfile.TemporaryDirectory() as tmpdir:
            code_path = Path(tmpdir) / filename
            code_path.write_text(code, encoding="utf-8")
            # Made world-writable so the non-root container user can create
            # files here (e.g. the compiled C++ binary); the directory is a
            # throwaway per-run temp dir, so the loosened mode is harmless.
            os.chmod(tmpdir, 0o777)

            if use_docker:
                safety = self._safety_flags()
                if ext == ".js":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", *safety, "-v", f"{tmpdir}:/workspace:ro", "-w", "/workspace", "node:20-alpine", "node", filename]
                elif ext == ".cpp":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", *safety, "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "gcc:13", "sh", "-c", f"g++ -O2 {filename} -o solution && ./solution"]
                else:
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", *safety, "-v", f"{tmpdir}:/workspace:ro", "-w", "/workspace", self.DOCKER_IMAGE, "python", filename]
                return await self._run_subprocess(cmd)
            else:
                if not _local_allowed():
                    raise LocalSandboxDisabledError(_LOCAL_DISABLED_MSG)
                # Local fallback execution (host, not isolated)
                if ext == ".js":
                    node_bin = shutil.which("node") or "node"
                    cmd = [node_bin, filename]
                elif ext == ".cpp":
                    gpp_bin = shutil.which("g++") or "g++"
                    exe_file = "solution.exe" if sys.platform == "win32" else "./solution"
                    cmd = [gpp_bin, "-O2", filename, "-o", "solution"]
                    build_res = await self._run_subprocess(cmd, cwd=tmpdir)
                    if not build_res["success"]:
                        build_res["stderr"] = "[WARNING: Running in local fallback mode]\n" + build_res["stderr"]
                        return build_res
                    cmd = [str(Path(tmpdir) / exe_file)]
                else:
                    cmd = [sys.executable, filename]

                res = await self._run_subprocess(cmd, cwd=tmpdir)
                res["stderr"] = "[WARNING: Running in local fallback mode without Docker sandbox]\n" + res["stderr"]
                return res

    async def run_tests(self, code: str, test_code: str, language: str = "Python") -> dict:
        use_docker = (not FORCE_LOCAL_SANDBOX) and (not ALLOW_LOCAL_SANDBOX) and (await check_docker())
        lang = language.lower()

        ext = ".py"
        test_ext = ".py"
        if "javascript" in lang or "js" in lang:
            ext = ".js"
            test_ext = ".test.js"
        elif "c++" in lang or "cpp" in lang:
            ext = ".cpp"
            test_ext = "_test.cpp"

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / f"solution{ext}").write_text(code, encoding="utf-8")
            (Path(tmpdir) / f"test_solution{test_ext}").write_text(test_code, encoding="utf-8")
            os.chmod(tmpdir, 0o777)

            if use_docker:
                if ext == ".js":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", *self._safety_flags(), "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "node:20-alpine", "node", "--test", f"test_solution{test_ext}"]
                elif ext == ".cpp":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", *self._safety_flags(), "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "gcc:13", "sh", "-c", f"g++ -O2 solution.cpp test_solution{test_ext} -o test_runner && ./test_runner"]
                else:
                    # Preferred path: a pre-built image with pytest already
                    # installed, so the test container can stay fully
                    # network-isolated (--network none) and run as non-root.
                    # Falls back to installing pytest at container start
                    # (requires root, and requires network — which
                    # contradicts --network none — kept only so this never
                    # hard-fails if the image build itself is unavailable).
                    if await _ensure_pytest_image():
                        image, test_cmd, non_root = _PYTEST_IMAGE, "pytest test_solution.py -v --tb=short 2>&1", True
                    else:
                        image, test_cmd, non_root = self.DOCKER_IMAGE, "pip install pytest -q 2>/dev/null && pytest test_solution.py -v --tb=short 2>&1", False
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", *self._safety_flags(non_root=non_root), "-v", f"{tmpdir}:/workspace", "-w", "/workspace", image, "sh", "-c", test_cmd]
                return await self._run_subprocess(cmd, timeout=60)
            else:
                if not _local_allowed():
                    raise LocalSandboxDisabledError(_LOCAL_DISABLED_MSG)
                # Local fallback test execution (host, not isolated)
                if ext == ".js":
                    node_bin = shutil.which("node") or "node"
                    cmd = [node_bin, "--test", f"test_solution{test_ext}"]
                elif ext == ".cpp":
                    gpp_bin = shutil.which("g++") or "g++"
                    exe_file = "test_runner.exe" if sys.platform == "win32" else "./test_runner"
                    compile_cmd = [gpp_bin, "-O2", f"solution{ext}", f"test_solution{test_ext}", "-o", "test_runner"]
                    compile_res = await self._run_subprocess(compile_cmd, cwd=tmpdir)
                    if not compile_res["success"]:
                        compile_res["stderr"] = "[WARNING: Running in local fallback mode]\nCompilation Error:\n" + compile_res["stderr"]
                        return compile_res
                    cmd = [str(Path(tmpdir) / exe_file)]
                else:
                    cmd = [sys.executable, "-m", "pytest", "test_solution.py", "-v", "--tb=short"]

                res = await self._run_subprocess(cmd, timeout=60, cwd=tmpdir)
                res["stderr"] = "[WARNING: Running in local fallback mode without Docker sandbox]\n" + res["stderr"]
                return res

    async def _run_subprocess(self, cmd: list, timeout: int = None, cwd: str = None) -> dict:
        timeout = timeout or self.TIMEOUT_SECONDS

        def run_sync():
            import subprocess
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    cwd=cwd,
                )
                return {
                    "stdout": res.stdout.decode("utf-8", errors="replace"),
                    "stderr": res.stderr.decode("utf-8", errors="replace"),
                    "exit_code": res.returncode,
                    "success": res.returncode == 0,
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired as e:
                stdout_str = e.stdout.decode("utf-8", errors="replace") if e.stdout else ""
                stderr_str = e.stderr.decode("utf-8", errors="replace") if e.stderr else "Execution timed out"
                return {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "exit_code": -1,
                    "success": False,
                    "timed_out": True,
                }
            except FileNotFoundError:
                raise FileNotFoundError

        try:
            return await asyncio.to_thread(run_sync)
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": "Execution binary not found.",
                "exit_code": -1,
                "success": False,
                "timed_out": False,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": -1,
                "success": False,
                "timed_out": False,
            }