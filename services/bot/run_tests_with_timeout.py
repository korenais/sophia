"""
Run notification tests with timeout handling and progress tracking
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Run notification tests with timeout and progress tracking"""
    print("=" * 80)
    print("NOTIFICATION SYSTEM TESTS - WITH TIMEOUT HANDLING")
    print("=" * 80)
    
    # Load environment from infra/.env
    env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
    if env_path.exists():
        print(f"[INFO] Loading environment from: {env_path}")
        load_dotenv(env_path)
    else:
        print(f"[WARN] .env file not found at {env_path}")
        load_dotenv()
    
    # Set environment variables
    os.environ["USE_REAL_BOT"] = "true"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # Change to bot directory
    bot_dir = Path(__file__).parent
    os.chdir(bot_dir)
    print(f"\n[INFO] Changed to directory: {os.getcwd()}\n")
    
    # Run pytest with timeout handling
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_notifications.py",
        "-v",                    # Verbose
        "-s",                    # Don't capture output
        "--tb=line",             # Line traceback (faster)
        "--asyncio-mode=auto",   # Auto async mode
        "--maxfail=10",          # Stop after 10 failures
        # "-x",                  # Stop on first failure (commented to see all failures)
        "--durations=10",        # Show 10 slowest tests
        # Uncomment for parallel execution (requires pytest-xdist):
        # "-n", "auto",          # Auto-detect CPU cores for parallel execution
    ]
    
    print(f"[INFO] Running command: {' '.join(cmd)}\n")
    print("=" * 80)
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, env=os.environ.copy(), check=False)
        elapsed = time.time() - start_time
        
        print()
        print("=" * 80)
        print(f"Test execution time: {elapsed:.2f} seconds")
        if result.returncode == 0:
            print("[SUCCESS] All tests passed!")
        else:
            print(f"[FAILED] Tests failed with exit code {result.returncode}")
        print("=" * 80)
        
        return result.returncode
    except KeyboardInterrupt:
        print("\n[INFO] Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"[ERROR] Failed to run tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
