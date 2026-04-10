"""
Run notification system unit tests with debug output
"""
import os
import sys
import subprocess

def main():
    """Run notification tests with verbose output"""
    print("=" * 80)
    print("NOTIFICATION SYSTEM UNIT TESTS")
    print("=" * 80)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    print("=" * 80)
    
    # Change to bot directory
    bot_dir = os.path.join(os.path.dirname(__file__))
    os.chdir(bot_dir)
    print(f"Changed to directory: {os.getcwd()}\n")
    
    # Run pytest
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_notifications.py",
        "-v",           # Verbose
        "-s",           # Don't capture output
        "--tb=short",   # Short traceback
        "--asyncio-mode=auto",  # Auto async mode
        "-x",           # Stop on first failure (optional, comment out for full run)
    ]
    
    print(f"Running command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("ERROR: pytest not found. Please install: pip install pytest pytest-asyncio")
        return 1
    except Exception as e:
        print(f"ERROR: Failed to run tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
