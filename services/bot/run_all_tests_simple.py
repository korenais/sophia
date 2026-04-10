"""
Простой запуск всех тестов с выводом прогресса
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)

os.environ["USE_REAL_BOT"] = "true"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

os.chdir(Path(__file__).parent)

# Run tests
cmd = [
    sys.executable,
    "-m", "pytest",
    "tests/test_notifications.py",
    "-v",
    "--tb=line",
    "--asyncio-mode=auto",
    "--maxfail=5",
    "--durations=10",
]

print("Запуск тестов...")
print("=" * 80)
sys.exit(os.system(" ".join(cmd)))
