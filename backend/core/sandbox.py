import asyncio
import tempfile
import os
import shutil
import sys
from pathlib import Path

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


class ExecutionSandbox:
    """
    Runs code inside a Docker container or local fallback sandbox.
    Supports Python, JavaScript, and C++.
    """

    DOCKER_IMAGE = "python:3.11-slim"
    TIMEOUT_SECONDS = 30

    async def run_code(self, code: str, language: str = "Python") -> dict:
        use_docker = (not FORCE_LOCAL_SANDBOX) and (await check_docker())
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

            if use_docker:
                if ext == ".js":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", "-v", f"{tmpdir}:/workspace:ro", "-w", "/workspace", "node:20-alpine", "node", filename]
                elif ext == ".cpp":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "gcc:latest", "sh", "-c", f"g++ -O2 {filename} -o solution && ./solution"]
                else:
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "256m", "-v", f"{tmpdir}:/workspace:ro", "-w", "/workspace", self.DOCKER_IMAGE, "python", filename]
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
        use_docker = (not FORCE_LOCAL_SANDBOX) and (await check_docker())
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

            if use_docker:
                if ext == ".js":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "node:20-alpine", "node", "--test", f"test_solution{test_ext}"]
                elif ext == ".cpp":
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", "-v", f"{tmpdir}:/workspace", "-w", "/workspace", "gcc:latest", "sh", "-c", f"g++ -O2 solution.cpp test_solution{test_ext} -o test_runner && ./test_runner"]
                else:
                    cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "512m", "-v", f"{tmpdir}:/workspace", "-w", "/workspace", self.DOCKER_IMAGE, "sh", "-c", "pip install pytest -q 2>/dev/null && pytest test_solution.py -v --tb=short 2>&1"]
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