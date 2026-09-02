import os
import requests
import yfinance as yf

# Telegram details from GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

# Stocks list (Nifty Top Stocks)
STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "TATAMOTORS.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "M&M.NS", "HINDUNILVR.NS", "BAJFINANCE.NS"
]

def check_zones(ticker):
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty or len(df) < 5:
            return
        
        last_close = float(df['Close'].iloc[-1])
        high_20 = float(df['High'].max())
        low_20 = float(df['Low'].min())
        
        # Supply Zone Check (Near 20-Day High)
        if abs(last_close - high_20) / high_20 < 0.015:
            msg = f"🔴 *SUPPLY ZONE ALERT*\n\nStock: `{ticker}`\nCurrent Price: ₹{last_close:.2f}\n20-Day High: ₹{high_20:.2f}"
            send_telegram_message(msg)
            
        # Demand Zone Check (Near 20-Day Low)
        elif abs(last_close - low_20) / low_20 < 0.015:
            msg = f"🟢 *DEMAND ZONE ALERT*\n\nStock: `{ticker}`\nCurrent Price: ₹{last_close:.2f}\n20-Day Low: ₹{low_20:.2f}"
            send_telegram_message(msg)

    except Exception as e:
        print(f"Error checking {ticker}: {e}")

if __name__ == "__main__":
    print("Starting Zone Scanner...")
    for stock in STOCKS:
        check_zones(stock)
    print("Scanning complete.")
