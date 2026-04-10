"""Test link formatting"""
# Test profile link formatting
profile_url = "http://localhost:8081/#/user/9000001"
profile_link_template = "👤 <b>Полный профиль:</b> <a href='{profile_url}'>Открыть профиль</a>"
profile_link_formatted = profile_link_template.format(profile_url=profile_url)

print("Profile link template:", profile_link_template)
print("Profile URL:", profile_url)
print("Formatted link:", profile_link_formatted)
print("\nChecking HTML structure:")
print("- Contains <a href=:", "<a href=" in profile_link_formatted)
print("- Contains closing >:", "'>" in profile_link_formatted)
print("- Contains </a>:", "</a>" in profile_link_formatted)

# Test name link formatting
match_name = "Test User"
telegram_username = "testuser9000001"
name_display = f'<a href="https://t.me/{telegram_username}">{match_name}</a>'
matched_with_template = "Мы подобрали для вас контакт: {name}"
matched_with_formatted = matched_with_template.format(name=name_display)

print("\n" + "="*70)
print("Name link formatting:")
print("Name display:", name_display)
print("Matched with template:", matched_with_template)
print("Matched with formatted:", matched_with_formatted)
print("\nChecking HTML structure:")
print("- Contains <a href=:", "<a href=" in matched_with_formatted)
print("- Contains closing >:", ">" in matched_with_formatted)
print("- Contains </a>:", "</a>" in matched_with_formatted)
