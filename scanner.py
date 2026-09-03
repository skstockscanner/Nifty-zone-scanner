import os
import requests

# Secrets से Token और Chat ID प्राप्त करना
token = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

# टेलीग्राम पर भेजा जाने वाला मैसेज
message = "🚀 *Nifty Zone Scanner Alert*\n\nबधाई हो! आपका टेलीग्राम बॉट अब सफलतापूर्वक चालू हो गया है और GitHub Actions से जुड़ चुका है।"

url = f"https://api.telegram.org/bot{token}/sendMessage"

payload = {
    "chat_id": chat_id,
    "text": message,
    "parse_mode": "Markdown"
}

response = requests.post(url, json=payload)

print("--- MESSAGE SEND STATUS ---")
print("Status Code:", response.status_code)
print("Response Text:", response.text)
print("---------------------------")
