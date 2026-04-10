"""
Run notification tests with real bot and database
Loads settings from infra/.env
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Run notification tests with real infrastructure"""
    print("=" * 80)
    print("NOTIFICATION SYSTEM TESTS - REAL BOT & DATABASE")
    print("=" * 80)
    
    # Load environment from infra/.env
    env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
    if env_path.exists():
        print(f"[INFO] Loading environment from: {env_path}")
        load_dotenv(env_path)
    else:
        print(f"[WARN] .env file not found at {env_path}")
        print(f"[INFO] Using system environment variables")
        load_dotenv()
    
    # Check required settings
    db_url = os.getenv("DB_URL", "postgresql://postgres:postgres@db:5432/postgres")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    group_id = os.getenv("TELEGRAM_GROUP_ID")
    
    print(f"\n[CONFIG] DB_URL: {db_url[:50]}..." if len(db_url) > 50 else f"[CONFIG] DB_URL: {db_url}")
    print(f"[CONFIG] TELEGRAM_TOKEN: {'SET' if telegram_token else 'NOT SET'}")
    print(f"[CONFIG] TELEGRAM_GROUP_ID: {group_id if group_id else 'NOT SET'}")
    print(f"[CONFIG] USE_REAL_BOT: true (enabled for real testing)")
    
    if not telegram_token:
        print("\n[ERROR] TELEGRAM_TOKEN not set in infra/.env")
        print("[ERROR] Cannot run tests with real bot")
        return 1
    
    # Set environment variable for tests
    os.environ["USE_REAL_BOT"] = "true"
    
    # Change to bot directory
    bot_dir = Path(__file__).parent
    os.chdir(bot_dir)
    print(f"\n[INFO] Changed to directory: {os.getcwd()}\n")
    
    # Run pytest with verbose output
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_notifications.py",
        "-v",           # Verbose
        "-s",           # Don't capture output (show prints)
        "--tb=line",    # Line traceback (faster)
        "--asyncio-mode=auto",  # Auto async mode
        "--maxfail=10",  # Stop after 10 failures
        # "-x",         # Stop on first failure (commented out for full run to see all results)
        "--durations=10",  # Show 10 slowest tests
    ]
    
    print(f"[INFO] Running command: {' '.join(cmd)}\n")
    print("=" * 80)
    print()
    
    try:
        result = subprocess.run(cmd, env=os.environ.copy(), check=False)
        
        print()
        print("=" * 80)
        if result.returncode == 0:
            print("[SUCCESS] All tests passed!")
        else:
            print(f"[FAILED] Tests failed with exit code {result.returncode}")
        print("=" * 80)
        
        if group_id:
            print(f"\n[INFO] Check your Telegram group (ID: {group_id}) to see test notifications")
            print("[INFO] Look for messages marked with 🧪 TEST NOTIFICATION")
        
        return result.returncode
    except FileNotFoundError:
        print("[ERROR] pytest not found. Please install: pip install pytest pytest-asyncio")
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to run tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
