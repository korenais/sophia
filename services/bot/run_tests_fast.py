"""
Run notification tests with optimizations for speed
Shows progress in real-time
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Run notification tests with optimizations"""
    print("=" * 80)
    print("NOTIFICATION SYSTEM TESTS - OPTIMIZED FOR SPEED")
    print("=" * 80)
    
    # Load environment from infra/.env
    env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Set environment variables
    os.environ["USE_REAL_BOT"] = "true"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUNBUFFERED"] = "1"  # Unbuffered output for real-time progress
    
    # Change to bot directory
    bot_dir = Path(__file__).parent
    os.chdir(bot_dir)
    
    # Run pytest with optimizations
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_notifications.py",
        "-v",                    # Verbose
        "--tb=line",             # Line traceback (faster)
        "--asyncio-mode=auto",   # Auto async mode
        "--maxfail=10",          # Stop after 10 failures
        "--durations=10",        # Show 10 slowest tests
    ]
    
    print(f"[INFO] Running optimized tests...\n")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # Run with unbuffered output
        result = subprocess.run(
            cmd, 
            env=os.environ.copy(), 
            check=False,
            text=True,
            bufsize=0  # Unbuffered
        )
        elapsed = time.time() - start_time
        
        print()
        print("=" * 80)
        print(f"Total execution time: {elapsed:.2f} seconds")
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
