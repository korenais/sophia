"""Debug profile link formation"""
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Check environment variables
vite_api_base_url = os.getenv("VITE_API_BASE_URL", "")
frontend_url = os.getenv("FRONTEND_URL", "")

print("Environment variables:")
print(f"VITE_API_BASE_URL: {vite_api_base_url}")
print(f"FRONTEND_URL: {frontend_url}")

# Simulate link formation like in match_system.py
frontend_url_processed = vite_api_base_url.replace("/api", "").rstrip("/")
if not frontend_url_processed:
    frontend_url_processed = frontend_url.rstrip("/")

print(f"\nProcessed frontend_url: {frontend_url_processed}")

test_user_id = 9000001

if frontend_url_processed and test_user_id:
    if "/api" in frontend_url_processed or ":8055" in frontend_url_processed:
        base_url = frontend_url_processed.replace("/api", "").replace(":8055", ":8081")
        profile_url = f"{base_url}/#/user/{test_user_id}"
    else:
        profile_url = f"{frontend_url_processed}/#/user/{test_user_id}"
    
    print(f"\nGenerated profile_url: {profile_url}")
    
    # Test different HTML formats
    print("\n" + "="*70)
    print("Testing HTML formats:")
    print("="*70)
    
    # Format 1: Double quotes with escaping
    format1 = f'👤 <b>Полный профиль:</b> <a href=\"{profile_url}\">Открыть профиль</a>'
    print(f"\nFormat 1 (double quotes escaped):")
    print(format1)
    print(f"Contains <a href=: {'<a href=' in format1}")
    
    # Format 2: Single quotes
    format2 = f"👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"
    print(f"\nFormat 2 (single quotes):")
    print(format2)
    print(f"Contains <a href=: {'<a href=' in format2}")
    
    # Format 3: Direct double quotes (no escaping in f-string)
    format3 = f'👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'
    print(f"\nFormat 3 (direct double quotes in f-string):")
    print(format3)
    print(f"Contains <a href=: {'<a href=' in format3}")
    
    # Format 4: Using .format() method
    template = '👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'
    format4 = template.format(profile_url=profile_url)
    print(f"\nFormat 4 (using .format() with double quotes):")
    print(format4)
    print(f"Contains <a href=: {'<a href=' in format4}")
    
    print("\n" + "="*70)
    print("Recommended format for Telegram HTML:")
    print("Format 4 (using .format() with double quotes) should work best")
    print("="*70)
else:
    print("\n[WARNING] No frontend URL configured!")
