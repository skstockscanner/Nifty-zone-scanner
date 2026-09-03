import os
import requests

# Secrets verification test
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

print(f"--- TELEGRAM SECRETS TEST ---")
print(f"Token length: {len(token) if token else 'NOT FOUND'}")
print(f"Chat ID length: {len(chat_id) if chat_id else 'NOT FOUND'}")

if token and chat_id:
    test_url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(test_url, data={'chat_id': chat_id, 'text': '🧪 Test alert from GitHub Actions!'})
    print(f"Direct Response Code: {res.status_code}")
    print(f"Direct Response Text: {res.text}")
print(f"-----------------------------")
