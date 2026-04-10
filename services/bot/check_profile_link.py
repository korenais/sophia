"""Check profile link formation and environment variables"""
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / "infra" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

print("=" * 70)
print("Checking Profile Link Configuration")
print("=" * 70)

# Check environment variables
vite_api_base_url = os.getenv("VITE_API_BASE_URL", "")
frontend_url = os.getenv("FRONTEND_URL", "")

print(f"\nVITE_API_BASE_URL: {vite_api_base_url}")
print(f"FRONTEND_URL: {frontend_url}")

# Simulate link formation
frontend_url_processed = vite_api_base_url.replace("/api", "").rstrip("/")
if not frontend_url_processed:
    frontend_url_processed = frontend_url.rstrip("/")

print(f"\nProcessed frontend_url: {frontend_url_processed}")

# Test user ID
test_user_id = 9000001

if frontend_url_processed:
    if "/api" in frontend_url_processed or ":8055" in frontend_url_processed:
        base_url = frontend_url_processed.replace("/api", "").replace(":8055", ":8081")
        profile_url = f"{base_url}/#/user/{test_user_id}"
    else:
        profile_url = f"{frontend_url_processed}/#/user/{test_user_id}"
    
    print(f"\nGenerated profile_url: {profile_url}")
    
    # Test HTML formatting
    profile_link_template = "👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"
    profile_link_formatted = profile_link_template.format(profile_url=profile_url)
    
    print(f"\nFormatted link:")
    print(profile_link_formatted)
    print(f"\nLink length: {len(profile_link_formatted)}")
    
    # Check if it's valid HTML
    if "<a href=" in profile_link_formatted and ">" in profile_link_formatted:
        print("\n[OK] HTML link structure looks correct")
    else:
        print("\n[ERROR] HTML link structure is incorrect!")
else:
    print("\n[WARNING] No frontend URL configured! Profile links will not be generated.")
