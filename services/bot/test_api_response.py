"""Test what API returns for Anton"""
import asyncio
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

API_BASE = os.getenv("VITE_API_BASE_URL", "http://localhost:8055").replace("/api", "").rstrip("/")
ANTON_USER_ID = 1541686636

async def test():
    try:
        url = f"{API_BASE}/api/users/{ANTON_USER_ID}"
        print(f"Fetching: {url}")
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                user_data = resp.json()
                print("=" * 70)
                print("API Response for Anton Anisimov")
                print("=" * 70)
                print(f"\nUser ID: {user_data.get('user_id')}")
                print(f"Name: {user_data.get('intro_name')}")
                print(f"\nmatches_disabled from API: {user_data.get('matches_disabled')}")
                print(f"Type: {type(user_data.get('matches_disabled'))}")
                
                if user_data.get('matches_disabled') is True:
                    print("\n[OK] API correctly returns matches_disabled = True")
                elif user_data.get('matches_disabled') is False:
                    print("\n[WARNING] API returns matches_disabled = False (but DB has True!)")
                elif user_data.get('matches_disabled') is None:
                    print("\n[WARNING] API returns matches_disabled = None")
                else:
                    print(f"\n[UNKNOWN] API returns matches_disabled = {user_data.get('matches_disabled')}")
            else:
                print(f"[ERROR] API returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
