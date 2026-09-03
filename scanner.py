import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload)
        print("Telegram Alert Sent. Status:", res.status_code)
    except Exception as e:
        print("Error sending Telegram message:", e)

def get_trend(df):
    if len(df) < 20:
        return "UNKNOWN"
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    if df['Close'].iloc[-1] > df['EMA20'].iloc[-1] and df['Close'].iloc[-2] > df['EMA20'].iloc[-2]:
        return "UP"
    elif df['Close'].iloc[-1] < df['EMA20'].iloc[-1] and df['Close'].iloc[-2] < df['EMA20'].iloc[-2]:
        return "DOWN"
    return "SIDEWAYS"

def analyze_candle(open_p, high_p, low_p, close_p):
    total_range = high_p - low_p
    if total_range == 0:
        return 0, 100
    body = abs(close_p - open_p)
    body_pct = (body / total_range) * 100
    wick_pct = 100 - body_pct
    return body_pct, wick_pct

def scan_stock(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        
        df_weekly = ticker.history(period="1y", interval="1wk")
        df_daily = ticker.history(period="6m", interval="1d")
        df_15m = ticker.history(period="1mo", interval="15m")

        if df_weekly.empty or df_daily.empty or df_15m.empty:
            return

        df_125m = df_15m.resample('125min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        # 1. Trends Check (Weekly, Daily, 125m UP)
        weekly_trend = get_trend(df_weekly)
        daily_trend = get_trend(df_daily)
        trend_125m = get_trend(df_125m)

        if not (weekly_trend == "UP" and daily_trend == "UP" and trend_125m == "UP"):
            return

        # 2. Daily Demand Zone Check (3 to 5 candles back)
        daily_demand_zone_found = False
        daily_zone_high = 0
        daily_zone_low = 0

        for i in range(3, 6):
            if len(df_daily) < i+1:
                break
            open_p, high_p, low_p, close_p = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
            b_pct, w_pct = analyze_candle(open_p, high_p, low_p, close_p)
            
            out_open, out_high, out_low, out_close = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
            out_b_pct, _ = analyze_candle(out_open, out_high, out_low, out_close)

            if b_pct <= 40 and out_b_pct >= 60 and out_close > out_open:
                daily_demand_zone_found = True
                daily_zone_high = high_p
                daily_zone_low = low_p
                break

        current_price = df_daily['Close'].iloc[-1]
        is_in_daily_zone = daily_demand_zone_found and (daily_zone_low <= current_price <= daily_zone_high * 1.005)

        if not is_in_daily_zone:
            return

        # 3. 15-Min Execution Check
        leg_in_b, leg_in_w = analyze_candle(df_15m['Open'].iloc[-3], df_15m['High'].iloc[-3], df_15m['Low'].iloc[-3], df_15m['Close'].iloc[-3])
        base_b, base_w = analyze_candle(df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2])
        leg_out_b, leg_out_w = analyze_candle(df_15m['Open'].iloc[-1], df_15m['High'].iloc[-1], df_15m['Low'].iloc[-1], df_15m['Close'].iloc[-1])

        valid_leg_in = leg_in_b >= 85 and leg_in_w <= 15
        valid_base = base_b <= 35 and base_w >= 65
        valid_leg_out = leg_out_b >= 75 and leg_out_w <= 20 and df_15m['Close'].iloc[-1] > df_15m['Open'].iloc[-1]

        if valid_leg_in and valid_base and valid_leg_out:
            msg = (
                f"🔥 *DEMAND ZONE TRIGGER: {name}* 🔥\n\n"
                f"📈 **Weekly Trend:** {weekly_trend}\n"
                f"📈 **Daily Trend:** {daily_trend}\n"
                f"📈 **125m Trend:** {trend_125m}\n\n"
                f"📍 **Daily Demand Zone:** {round(daily_zone_low, 2)} - {round(daily_zone_high, 2)}\n"
                f"⚡ **15-Min Candle Structure:**\n"
                f"• Leg-in Body: {round(leg_in_b, 1)}%\n"
                f"• Base Body: {round(base_b, 1)}%\n"
                f"• Leg-out Body: {round(leg_out_b, 1)}%\n\n"
                f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                "✅ *Large/Mid Cap Setup Matched!*"
            )
            send_telegram_alert(msg)

    except Exception as e:
        print(f"Error scanning {symbol}: {e}")

def main():
    # Large-Cap & Top Mid-Cap Stock List (NSE)
    watchlist = {
        "^NSEI": "NIFTY 50 INDEX",
        "RELIANCE.NS": "Reliance Industries",
        "TCS.NS": "TCS",
        "HDFCBANK.NS": "HDFC Bank",
        "ICICIBANK.NS": "ICICI Bank",
        "INFY.NS": "Infosys",
        "BHARTIARTL.NS": "Bharti Airtel",
        "ITC.NS": "ITC",
        "SBIN.NS": "State Bank of India",
        "LTIM.NS": "LTIMindtree",
        "TATAMOTORS.NS": "Tata Motors",
        "AXISBANK.NS": "Axis Bank",
        "KOTAKBANK.NS": "Kotak Mahindra Bank",
        "LT.NS": "Larsen & Toubro",
        "HCLTECH.NS": "HCL Tech",
        "ASIANPAINT.NS": "Asian Paints",
        "MARUTI.NS": "Maruti Suzuki",
        "SUNPHARMA.NS": "Sun Pharma",
        "TITAN.NS": "Titan Company",
        "BAJFINANCE.NS": "Bajaj Finance",
        "TATASTEEL.NS": "Tata Steel",
        "NTPC.NS": "NTPC",
        "POWERGRID.NS": "Power Grid",
        "M&M.NS": "Mahindra & Mahindra",
        "ULTRACEMCO.NS": "UltraTech Cement",
        "PERSISTENT.NS": "Persistent Systems (Midcap)",
        "COFORGE.NS": "Coforge (Midcap)",
        "POLYCAB.NS": "Polycab India (Midcap)",
        "DIXON.NS": "Dixon Technologies (Midcap)",
        "TRENT.NS": "Trent (Midcap/Largecap)",
        "BEL.NS": "Bharat Electronics",
        "HAL.NS": "Hindustan Aeronautics",
        "VOLTAS.NS": "Voltas (Midcap)",
        "AUROPHARMA.NS": "Aurobindo Pharma (Midcap)"
    }

    print("Starting Scan for Large & Mid Cap Stocks...")
    for symbol, name in watchlist.items():
        scan_stock(symbol, name)

if __name__ == "__main__":
    main()
