"""Test profile link HTML formatting"""
profile_url = "http://localhost:8081/#/user/9000001"

# Test the format from scenes.py
profile_link_template = '👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>'
formatted = profile_link_template.format(profile_url=profile_url)

print("Template:", profile_link_template)
print("Profile URL:", profile_url)
print("Formatted:", formatted)
print("\nHTML structure check:")
print("- Has <a href=:", "<a href=" in formatted)
print("- Has closing >:", ">" in formatted)
print("- Has </a>:", "</a>" in formatted)
print("- URL in href:", profile_url in formatted)

# Test full message
message = f"Test message\n{formatted}"
print("\nFull message preview:")
print(message.replace("👤", "[USER]").replace("Полный", "Full"))
