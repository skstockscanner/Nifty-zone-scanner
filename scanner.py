import os
import yfinance as yf
import pandas as pd
import requests
import warnings
warnings.filterwarnings("ignore")

# 1. Telegram Secrets
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 2. Nifty Large Cap & Mid Cap Stocks List
STOCKS = [
    # Large Cap
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "L&T.NS", "TATAMOTORS.NS", 
    "M&M.NS", "SUNPHARMA.NS", "MARUTI.NS", "NTPC.NS", "KOTAKBANK.NS",
    # Mid Cap
    "TRENT.NS", "TVSMOTOR.NS", "DIXON.NS", "BHEL.NS", "IDFCFIRSTB.NS",
    "ZOMATO.NS", "SUZLON.NS", "PNB.NS", "POLYCAB.NS", "CUMMINSIND.NS"
]

def send_telegram_alert(message):
    """Telegram पर अलर्ट भेजने का फ़ंक्शन"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_trend_up(df):
    """चेक करता है कि ट्रेंड UP (Price > 20 SMA) है या नहीं"""
    if df.empty or len(df) < 20:
        return False
    sma20 = df['Close'].rolling(window=20).mean()
    return df['Close'].iloc[-1] > sma20.iloc[-1]

def analyze_candle(row):
    """कैंडल में Body % और Wick % निकालता है"""
    total_range = row['High'] - row['Low']
    if total_range == 0:
        return 0.0, 100.0
    body_size = abs(row['Close'] - row['Open'])
    body_pct = (body_size / total_range) * 100
    wick_pct = 100.0 - body_pct
    return body_pct, wick_pct

def scan_stock(ticker):
    """आपके सटीक डेली डिमांड ज़ोन रूल के अनुसार स्कैनिंग"""
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Multi-Timeframe Trend Fetching
        df_m = stock.history(period="2y", interval="1mo")
        df_w = stock.history(period="1y", interval="1wk")
        df_d = stock.history(period="6mo", interval="1d")
        df_125m = stock.history(period="1mo", interval="60m") # 125m proxy via 60m
        df_15m = stock.history(period="7d", interval="15m")

        # ट्रेंड अलाइनमेंट: Monthly, Weekly, 125-Min, और 15-Min पर Trend UP होना चाहिए
        trend_m = check_trend_up(df_m)
        trend_w = check_trend_up(df_w)
        trend_125 = check_trend_up(df_125m)
        trend_15 = check_trend_up(df_15m)

        if not (trend_m and trend_w and trend_125 and trend_15):
            return None # अगर कोई एक भी ट्रेंड Up नहीं है, तो तुरंत रिजेक्ट करें

        # 2. Daily Chart Demand Zone Requirement
        if df_d.empty or len(df_d) < 10:
            return None

        total_candles = len(df_d)
        stock_name = ticker.replace('.NS', '')
        latest_close = float(df_d['Close'].iloc[-1])

        # रूल: लाइव कैंडल से 3-4 कैंडल पीछे ही डिमांड ज़ोन होना चाहिए
        # idx = total_candles - 5 (Leg-In), idx+1 = Base (1 Single Base), idx+2 = Leg-Out
        for idx in range(total_candles - 5, total_candles - 3):
            leg_in = df_d.iloc[idx]
            base = df_d.iloc[idx + 1]       # केवल 1 सिंगल बेस कैंडल
            leg_out = df_d.iloc[idx + 2]

            body_leg_in, wick_leg_in = analyze_candle(leg_in)
            body_base, wick_base = analyze_candle(base)
            body_leg_out, wick_leg_out = analyze_candle(leg_out)

            # Strict Candle Criteria Check:
            # 1. Leg-In: Body >= 85-90%
            # 2. Base: Body <= 30%, Wick >= 70% (Single Base Candle)
            # 3. Leg-Out: Body >= 85-90% (Green Candle)
            is_leg_in_valid = (body_leg_in >= 85.0)
            is_single_base_valid = (body_base <= 30.0 and wick_base >= 70.0)
            is_leg_out_valid = (body_leg_out >= 85.0 and leg_out['Close'] > leg_out['Open'])

            if is_leg_in_valid and is_single_base_valid and is_leg_out_valid:
                zone_low = float(base['Low'])
                zone_high = float(base['High'])
                
                # 3. Freshness Check (क्या प्राइस बनने के बाद वापस ज़ोन तोड़ चुका है?)
                # Leg-Out बनने के बाद से लेकर लाइव कैंडल तक प्राइस ज़ोन के नीचे नहीं गया होना चाहिए
                post_zone_candles = df_d.iloc[idx + 3:]
                is_fresh = True
                for _, row in post_zone_candles.iterrows():
                    if row['Low'] < zone_low:
                        is_fresh = False
                        break

                if is_fresh:
                    return (f"🎯 *PERFECT DAILY DEMAND ZONE (FRESH)*\n\n"
                            f"📈 *Stock:* {stock_name}\n"
                            f"💰 *Current Price:* ₹{latest_close:.2f}\n"
                            f"🛡️ *Daily Demand Zone (1 Base):* ₹{zone_low:.2f} - ₹{zone_high:.2f}\n"
                            f"⏳ *Recency:* Exactly 3-4 candles behind live candle\n"
                            f"✅ *Trend Alignment:* Monthly, Weekly, 125m & 15m ALL UP\n"
                            f"⚡ *Execution:* 15m Trend & Fresh Alignment OK")

        return None
    except Exception as e:
        print(f"Error scanning {ticker}: {e}")
        return None

def main():
    print("🚀 Running Precision Daily Demand Zone Scanner...")
    found_alerts = []
    
    for stock in STOCKS:
        print(f"Scanning {stock}...")
        alert = scan_stock(stock)
        if alert:
            found_alerts.append(alert)
            
    if found_alerts:
        for msg in found_alerts:
            send_telegram_alert(msg)
    else:
        print("No stocks matched the strict single-base fresh demand zone criteria today.")
        send_telegram_alert("⚙️ *Scanner Update:* Today, no stocks matched all strict Daily Zone (Single Base) & MTF Trend criteria.")

if __name__ == "__main__":
    main()
