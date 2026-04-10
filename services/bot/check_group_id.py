"""Check TELEGRAM_GROUP_ID"""
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
load_dotenv(env_path)

group_id = os.getenv('TELEGRAM_GROUP_ID')
print(f'TELEGRAM_GROUP_ID: {group_id if group_id else "NOT SET"}')
