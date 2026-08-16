import asyncio
import sys
import os

# Force local fallback mode for testing
os.environ["FORCE_LOCAL_SANDBOX"] = "true"

from core.sandbox import ExecutionSandbox

async def verify_sandbox():
    sandbox = ExecutionSandbox()
    
    from core.sandbox import check_docker
    docker_ok = await check_docker()
    print(f"Docker detected and running: {docker_ok}")
    
    print("=" * 60)
    print("1. Testing run_code (Executing a simple script locally)...")
    print("=" * 60)
    code = "print('Hello from local execution sandbox fallback!')"
    res = await sandbox.run_code(code)
    
    print("\nResult:")
    print(f"Success:   {res.get('success')}")
    print(f"Exit Code: {res.get('exit_code')}")
    print(f"Stdout:    {res.get('stdout').strip()}")
    print(f"Stderr:\n{res.get('stderr')}")
    
    print("=" * 60)
    print("2. Testing run_tests (Running a pytest suite locally)...")
    print("=" * 60)
    solution_code = """
def add(a, b):
    return a + b
"""
    test_code = """
from solution import add
def test_add():
    assert add(2, 3) == 5
"""
    res_tests = await sandbox.run_tests(solution_code, test_code)
    
    print("\nResult:")
    print(f"Success:   {res_tests.get('success')}")
    print(f"Exit Code: {res_tests.get('exit_code')}")
    print(f"Stdout:\n{res_tests.get('stdout').strip()}")
    print(f"Stderr:\n{res_tests.get('stderr')}")
    print("=" * 60)

if __name__ == "__main__":
    # Ensure pytest is installed in the active environment
    try:
        import pytest
    except ImportError:
        print("[ERROR] pytest is not installed. Please run:")
        print("  pip install pytest")
        sys.exit(1)
        
    asyncio.run(verify_sandbox())
