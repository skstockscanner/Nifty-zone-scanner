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
            return False

        df_125m = df_15m.resample('125min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        weekly_trend = get_trend(df_weekly)
        daily_trend = get_trend(df_daily)
        trend_125m = get_trend(df_125m)
        current_price = df_daily['Close'].iloc[-1]

        triggered = False

        # =========================================================
        # 1. DEMAND ZONE CHECK (BULLISH SETUP)
        # =========================================================
        if weekly_trend == "UP" and daily_trend == "UP" and trend_125m == "UP":
            daily_dz_found = False
            dz_high, dz_low = 0, 0

            for i in range(3, 6):
                if len(df_daily) < i+1:
                    break
                o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, _ = analyze_candle(o, h, l, c)
                
                out_o, out_h, out_l, out_c = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                out_b_pct, _ = analyze_candle(out_o, out_h, out_l, out_c)

                # Base Body <= 40% & Leg-out Green Candle >= 60%
                if b_pct <= 40 and out_b_pct >= 60 and out_c > out_o:
                    daily_dz_found = True
                    dz_high, dz_low = h, l
                    break

            if daily_dz_found and (dz_low <= current_price <= dz_high * 1.005):
                leg_in_b, leg_in_w = analyze_candle(df_15m['Open'].iloc[-3], df_15m['High'].iloc[-3], df_15m['Low'].iloc[-3], df_15m['Close'].iloc[-3])
                base_b, base_w = analyze_candle(df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2])
                leg_out_b, leg_out_w = analyze_candle(df_15m['Open'].iloc[-1], df_15m['High'].iloc[-1], df_15m['Low'].iloc[-1], df_15m['Close'].iloc[-1])

                valid_in = leg_in_b >= 85 and leg_in_w <= 15
                valid_base = base_b <= 35 and base_w >= 65
                valid_out = leg_out_b >= 75 and leg_out_w <= 20 and df_15m['Close'].iloc[-1] > df_15m['Open'].iloc[-1]

                if valid_in and valid_base and valid_out:
                    msg = (
                        f"🔥 *DEMAND ZONE TRIGGER: {name} ({symbol})* 🔥\n\n"
                        f"📈 **Weekly Trend:** {weekly_trend}\n"
                        f"📈 **Daily Trend:** {daily_trend}\n"
                        f"📈 **125m Trend:** {trend_125m}\n\n"
                        f"📍 **Daily Demand Zone:** {round(dz_low, 2)} - {round(dz_high, 2)}\n"
                        f"⚡ **15-Min Candle Structure:**\n"
                        f"• Leg-in Body: {round(leg_in_b, 1)}%\n"
                        f"• Base Body: {round(base_b, 1)}%\n"
                        f"• Leg-out Body (Green): {round(leg_out_b, 1)}%\n\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                        "✅ *Bullish Demand Zone Matched!*"
                    )
                    send_telegram_alert(msg)
                    triggered = True

        # =========================================================
        # 2. SUPPLY ZONE CHECK (BEARISH SETUP)
        # =========================================================
        if weekly_trend == "DOWN" and daily_trend == "DOWN" and trend_125m == "DOWN":
            daily_sz_found = False
            sz_high, sz_low = 0, 0

            for i in range(3, 6):
                if len(df_daily) < i+1:
                    break
                o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, _ = analyze_candle(o, h, l, c)
                
                out_o, out_h, out_l, out_c = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                out_b_pct, _ = analyze_candle(out_o, out_h, out_l, out_c)

                # Base Body <= 40% & Leg-out Red Candle >= 60%
                if b_pct <= 40 and out_b_pct >= 60 and out_c < out_o:
                    daily_sz_found = True
                    sz_high, sz_low = h, l
                    break

            if daily_sz_found and (sz_low * 0.995 <= current_price <= sz_high):
                leg_in_b, leg_in_w = analyze_candle(df_15m['Open'].iloc[-3], df_15m['High'].iloc[-3], df_15m['Low'].iloc[-3], df_15m['Close'].iloc[-3])
                base_b, base_w = analyze_candle(df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2])
                leg_out_b, leg_out_w = analyze_candle(df_15m['Open'].iloc[-1], df_15m['High'].iloc[-1], df_15m['Low'].iloc[-1], df_15m['Close'].iloc[-1])

                valid_in = leg_in_b >= 85 and leg_in_w <= 15
                valid_base = base_b <= 35 and base_w >= 65
                valid_out = leg_out_b >= 75 and leg_out_w <= 20 and df_15m['Close'].iloc[-1] < df_15m['Open'].iloc[-1] # Red Leg-out

                if valid_in and valid_base and valid_out:
                    msg = (
                        f"🔻 *SUPPLY ZONE TRIGGER: {name} ({symbol})* 🔻\n\n"
                        f"📉 **Weekly Trend:** {weekly_trend}\n"
                        f"📉 **Daily Trend:** {daily_trend}\n"
                        f"📉 **125m Trend:** {trend_125m}\n\n"
                        f"📍 **Daily Supply Zone:** {round(sz_low, 2)} - {round(sz_high, 2)}\n"
                        f"⚡ **15-Min Candle Structure:**\n"
                        f"• Leg-in Body: {round(leg_in_b, 1)}%\n"
                        f"• Base Body: {round(base_b, 1)}%\n"
                        f"• Leg-out Body (Red): {round(leg_out_b, 1)}%\n\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                        "✅ *Bearish Supply Zone Matched!*"
                    )
                    send_telegram_alert(msg)
                    triggered = True

        return triggered

    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return False

def main():
    watchlist = {
        "^NSEI": "NIFTY 50 INDEX",
        "RELIANCE.NS": "Reliance Industries", "TCS.NS": "TCS", "HDFCBANK.NS": "HDFC Bank",
        "ICICIBANK.NS": "ICICI Bank", "INFY.NS": "Infosys", "BHARTIARTL.NS": "Bharti Airtel",
        "ITC.NS": "ITC", "SBIN.NS": "State Bank of India", "LTIM.NS": "LTIMindtree",
        "TATAMOTORS.NS": "Tata Motors", "AXISBANK.NS": "Axis Bank", "KOTAKBANK.NS": "Kotak Bank",
        "LT.NS": "Larsen & Toubro", "HCLTECH.NS": "HCL Tech", "ASIANPAINT.NS": "Asian Paints",
        "MARUTI.NS": "Maruti Suzuki", "SUNPHARMA.NS": "Sun Pharma", "TITAN.NS": "Titan",
        "BAJFINANCE.NS": "Bajaj Finance", "TATASTEEL.NS": "Tata Steel", "NTPC.NS": "NTPC",
        "POWERGRID.NS": "Power Grid", "M&M.NS": "Mahindra & Mahindra", "ULTRACEMCO.NS": "UltraTech Cement",
        "COALINDIA.NS": "Coal India", "HDFCLIFE.NS": "HDFC Life", "PIDILITIND.NS": "Pidilite",
        "GRASIM.NS": "Grasim", "TECHM.NS": "Tech Mahindra", "HINDUNILVR.NS": "Hindustan Unilever",
        "ADANIENT.NS": "Adani Enterprises", "ADANIPORTS.NS": "Adani Ports", "ONGC.NS": "ONGC",
        "JSWSTEEL.NS": "JSW Steel", "TRENT.NS": "Trent", "BEL.NS": "Bharat Electronics",
        "HAL.NS": "Hindustan Aeronautics", "SIEMENS.NS": "Siemens", "ABB.NS": "ABB India",
        "DLF.NS": "DLF", "VBL.NS": "Varun Beverages", "IOC.NS": "IOC", "REC.NS": "REC Ltd",
        "PFC.NS": "PFC", "BANKBARODA.NS": "Bank of Baroda", "GAIL.NS": "GAIL",
        "INDIGO.NS": "InterGlobe Aviation", "CHOLAFIN.NS": "Cholamandalam", "TVSMOTOR.NS": "TVS Motor",
        "HINDALCO.NS": "Hindalco", "EICHERMOT.NS": "Eicher Motors", "BPCL.NS": "BPCL",
        "DIVISLAB.NS": "Divis Labs", "CIPLA.NS": "Cipla", "DRREDDY.NS": "Dr Reddys",
        "APOLLOHOSP.NS": "Apollo Hospitals", "GODREJCP.NS": "Godrej Consumer", "BRITANNIA.NS": "Britannia",
        "TATACONSUM.NS": "Tata Consumer", "SHREECEM.NS": "Shree Cement", "BAJAJ-AUTO.NS": "Bajaj Auto",
        "HEROMOTOCO.NS": "Hero MotoCorp", "SBILIFE.NS": "SBI Life", "ICICIPRULI.NS": "ICICI Prudential",
        "ICICIGI.NS": "ICICI Lombard", "BERGEPAINT.NS": "Berger Paints", "DABUR.NS": "Dabur",
        "MARICO.NS": "Marico", "AMBUJACEM.NS": "Ambuja Cements", "MUTHOOTFIN.NS": "Muthoot Finance",
        "BOSCHLTD.NS": "Bosch", "MAXHEALTH.NS": "Max Healthcare", "LICI.NS": "LIC India",
        "JIOFIN.NS": "Jio Financial", "TATAPOWER.NS": "Tata Power", "RVNL.NS": "RVNL",
        "MAZDOCK.NS": "Mazagon Dock", "BHEL.NS": "BHEL", "NHPC.NS": "NHPC", "SJVN.NS": "SJVN",
        "SUZLON.NS": "Suzlon", "IDFCFIRSTB.NS": "IDFC First Bank", "AUBANK.NS": "AU Small Finance",
        "FEDERALBNK.NS": "Federal Bank", "BANDHANBNK.NS": "Bandhan Bank", "PNB.NS": "PNB",
        "CANBK.NS": "Canara Bank", "UNIONBANK.NS": "Union Bank", "BANKINDIA.NS": "Bank of India",
        "INDIANB.NS": "Indian Bank", "PERSISTENT.NS": "Persistent Systems", "COFORGE.NS": "Coforge",
        "POLYCAB.NS": "Polycab", "DIXON.NS": "Dixon Tech", "VOLTAS.NS": "Voltas",
        "AUROPHARMA.NS": "Aurobindo Pharma", "ESCORTS.NS": "Escorts Kubota", "BALKRISIND.NS": "Balkrishna Ind",
        "CONCOR.NS": "CONCOR", "GUJGASLTD.NS": "Gujarat Gas", "M&MFIN.NS": "M&M Finance",
        "IPCALAB.NS": "Ipca Labs", "ALKEM.NS": "Alkem Labs", "LUPIN.NS": "Lupin",
        "BIOCON.NS": "Biocon", "SYNGENE.NS": "Syngene", "TATACOMM.NS": "Tata Comm",
        "MOTHERSON.NS": "Samvardhana Motherson", "BATAINDIA.NS": "Bata India", "KAJARIACER.NS": "Kajaria Ceramics",
        "SUPREMEIND.NS": "Supreme Ind", "ASTRAL.NS": "Astral", "PAGEIND.NS": "Page Industries",
        "RELAXO.NS": "Relaxo", "CROMPTON.NS": "Crompton Greaves", "LAURUSLABS.NS": "Laurus Labs",
        "DEEPAKNTR.NS": "Deepak Nitrite", "TATAELXSI.NS": "Tata Elxsi", "LTTS.NS": "L&T Tech",
        "KPITTECH.NS": "KPIT Tech", "CYIENT.NS": "Cyient", "SONACOMS.NS": "Sona BLW",
        "BSOFT.NS": "BirlaSoft", "HAPPSTMNDS.NS": "Happiest Minds", "ZEEL.NS": "Zee Entertainment",
        "SUNTV.NS": "Sun TV", "PVRINOX.NS": "PVR Inox", "METROPOLIS.NS": "Metropolis",
        "LALPATHLAB.NS": "Dr Lal PathLab", "TORNTPHARM.NS": "Torrent Pharma", "GLENMARK.NS": "Glenmark",
        "ABFRL.NS": "Aditya Birla Fashion", "GODREJPROP.NS": "Godrej Properties", "OBEROIRLTY.NS": "Oberoi Realty",
        "PHOENIXLTD.NS": "Phoenix Mills", "PRESTIGE.NS": "Prestige Estate", "SOBHA.NS": "Sobha",
        "INDHOTEL.NS": "Indian Hotels", "LEMONTREE.NS": "Lemon Tree", "RAYMOND.NS": "Raymond",
        "MANYAVAR.NS": "Vedant Fashions", "VIPIND.NS": "VIP Industries", "RADICO.NS": "Radico Khaitan",
        "UBL.NS": "United Breweries", "MCDOWELL-N.NS": "United Spirits", "AMBER.NS": "Amber Enterprises",
        "KEI.NS": "KEI Industries", "APARINDS.NS": "Apar Industries", "SCHAEFFLER.NS": "Schaeffler India",
        "TIMKEN.NS": "Timken India", "SKFINDIA.NS": "SKF India", "BHARATFORG.NS": "Bharat Forge",
        "CUMMINSIND.NS": "Cummins India", "THERMAX.NS": "Thermax", "CGPOWER.NS": "CG Power",
        "CARBORUN.NS": "Carborundum Universal", "AIAENG.NS": "AIA Engineering", "KEC.NS": "KEC International",
        "KALPATPOWR.NS": "Kalpataru Projects", "NCC.NS": "NCC", "PNCINFRA.NS": "PNC Infratech", "IRB.NS": "IRB Infrastructure",
        "JINDALSTEL.NS": "Jindal Steel", "SAIL.NS": "SAIL", "NMDC.NS": "NMDC",
        "MOIL.NS": "MOIL", "HINDZINC.NS": "Hindustan Zinc", "HINDCOPPER.NS": "Hindustan Copper",
        "NATIONALUM.NS": "NALCO", "APLAPOLLO.NS": "APL Apollo", "RATNAMANI.NS": "Ratnamani Metals",
        "COCHINSHIP.NS": "Cochin Shipyard", "GRSE.NS": "Garden Reach", "BEML.NS": "BEML",
        "DATAPATTNS.NS": "Data Patterns", "MAPMYINDIA.NS": "CE Info Systems", "TANLA.NS": "Tanla Platforms",
        "INTELLECT.NS": "Intellect Design", "AFFLE.NS": "Affle India", "LATENTVIEW.NS": "Latent View",
        "NAUKRI.NS": "Info Edge", "POLICYBZR.NS": "PB Fintech", "PAYTM.NS": "One97 Paytm",
        "ZOMATO.NS": "Zomato", "NYKAA.NS": "FSN E-Commerce", "DELHIVERY.NS": "Delhivery",
        "PATANJALI.NS": "Patanjali Foods", "ADANIPOWER.NS": "Adani Power", "ADANIGREEN.NS": "Adani Green",
        "ADANITRANS.NS": "Adani Energy Solutions", "ADANIWILMAR.NS": "Adani Wilmar",
        "ATGL.NS": "Adani Total Gas", "GSPL.NS": "Gujarat State Petronet", "IGL.NS": "Indraprastha Gas", "MGL.NS": "Mahanagar Gas",
        "PETRONET.NS": "Petronet LNG", "OIL.NS": "Oil India", "MANAPPURAM.NS": "Manappuram Finance",
        "IIFL.NS": "IIFL Finance", "CREDITACC.NS": "CreditAccess Grameen", "POONAWALLA.NS": "Poonawalla Fincorp",
        "FIVESTAR.NS": "Five-Star Business", "HOMEFIRST.NS": "Home First Finance", "APTUS.NS": "Aptus Value Housing",
        "CANFINHOME.NS": "Can Fin Homes", "HUDCO.NS": "HUDCO", "IRCTC.NS": "IRCTC", "RAILTEL.NS": "RailTel", "RITES.NS": "RITES",
        "CENTURYTEX.NS": "Century Textiles", "TRIDENT.NS": "Trident", "ALOKINDS.NS": "Alok Industries",
        "KPRMILL.NS": "KPR Mill", "WELSPUNLIV.NS": "Welspun Living", "GMDCLTD.NS": "GMDC",
        "CHENNPETRO.NS": "Chennai Petroleum", "MRPL.NS": "MRPL", "CASTROLIND.NS": "Castrol India",
        "FINPIPE.NS": "Finolex Pipes", "FINCABLES.NS": "Finolex Cables", "ROUTE.NS": "Route Mobile"
    }

    print("Starting Dual Scan (Demand + Supply) for 250+ Stocks...")
    total_scanned = len(watchlist)
    matched_count = 0

    for symbol, name in watchlist.items():
        if scan_stock(symbol, name):
            matched_count += 1

    summary_msg = (
        "🤖 *DEMAND & SUPPLY SCANNER COMPLETED!*\n\n"
        "✅ **250 स्टॉक्स का डुअल स्कैन पूरा हुआ!**\n"
        f"📊 **कुल स्कैन किए गए स्टॉक्स:** {total_scanned}\n"
        f"🎯 **ट्रिगर हुए कुल सेटअप:** {matched_count}\n\n"
        "🟢 *आपका बोट अब तेजी (Demand) और मंदी (Supply) दोनों को स्कैन कर रहा है!*"
    )
    send_telegram_alert(summary_msg)

if __name__ == "__main__":
    main()
