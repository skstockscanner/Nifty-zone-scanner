import os
import requests

token = os.getenv('TELEGRAM_TOKEN')
url = f"https://api.telegram.org/bot{token}/getUpdates"

response = requests.get(url)
print("--- TELEGRAM CHAT ID CHECK ---")
print(response.text)
print("------------------------------")
