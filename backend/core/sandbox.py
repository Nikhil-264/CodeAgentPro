import asyncio
import tempfile
import os
import shutil
import sys
from pathlib import Path

_DOCKER_AVAILABLE = None
FORCE_LOCAL_SANDBOX = os.getenv("FORCE_LOCAL_SANDBOX", "false").lower() == "true"


async def check_docker() -> bool:
    global _DOCKER_AVAILABLE
    if _DOCKER_AVAILABLE is not None:
        return _DOCKER_AVAILABLE

    if not shutil.which("docker"):
        _DOCKER_AVAILABLE = False
        return False

    try:
        import subprocess
        # Run a quick check to see if the Docker daemon is actually running
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
    Stage 2: Runs code inside a Docker container.
    Prevents the generated code from touching the host system.
    """

    DOCKER_IMAGE = "python:3.11-slim"
    TIMEOUT_SECONDS = 30

    async def run_code(self, code: str, filename: str = "solution.py") -> dict:
        """
        Write code to a temp file and execute it inside Docker.
        Falls back to local execution if Docker is not available.

        Returns:
            {
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "success": bool,
                "timed_out": bool
            }
        """
        use_docker = (not FORCE_LOCAL_SANDBOX) and (await check_docker())
        with tempfile.TemporaryDirectory() as tmpdir:
            code_path = Path(tmpdir) / filename
            code_path.write_text(code)

            if use_docker:
                cmd = [
                    "docker", "run", "--rm",
                    "--network", "none",          # No internet access
                    "--memory", "256m",           # Memory cap
                    "--cpus", "1.0",              # CPU cap
                    "--pids-limit", "64",         # Prevent fork bombs
                    "-v", f"{tmpdir}:/workspace:ro",  # Read-only mount
                    "-w", "/workspace",
                    self.DOCKER_IMAGE,
                    "python", filename
                ]
                return await self._run_subprocess(cmd)
            else:
                # Fallback to local python execution
                cmd = [sys.executable, filename]
                res = await self._run_subprocess(cmd, cwd=tmpdir)
                res["stderr"] = "[WARNING: Running in local fallback mode without Docker sandbox]\n" + res["stderr"]
                return res

    async def run_tests(self, code: str, test_code: str) -> dict:
        """
        Run pytest against the generated code inside Docker.
        Falls back to local execution if Docker is not available.
        Both files are written to a temp folder and run.
        """
        use_docker = (not FORCE_LOCAL_SANDBOX) and (await check_docker())
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "solution.py").write_text(code)
            (Path(tmpdir) / "test_solution.py").write_text(test_code)

            if use_docker:
                # Install pytest then run tests inside Docker container
                cmd = [
                    "docker", "run", "--rm",
                    "--network", "none",
                    "--memory", "512m",
                    "--cpus", "1.0",
                    "--pids-limit", "128",
                    "-v", f"{tmpdir}:/workspace",
                    "-w", "/workspace",
                    self.DOCKER_IMAGE,
                    "sh", "-c",
                    "pip install pytest -q 2>/dev/null && pytest test_solution.py -v --tb=short 2>&1"
                ]
                return await self._run_subprocess(cmd, timeout=60)
            else:
                # Fallback to local pytest execution using sys.executable
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
                "stderr": "Docker not found. Make sure Docker is installed and running.",
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