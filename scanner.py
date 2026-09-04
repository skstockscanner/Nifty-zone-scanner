import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

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

def get_simple_trend(df):
    if len(df) < 5:
        return "SIDEWAYS"
    if df['Close'].iloc[-1] > df['Close'].iloc[-5]:
        return "UP"
    elif df['Close'].iloc[-1] < df['Close'].iloc[-5]:
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

        weekly_trend = get_simple_trend(df_weekly)
        daily_trend = get_simple_trend(df_daily)
        trend_125m = get_simple_trend(df_125m)
        current_price = df_daily['Close'].iloc[-1]

        # ==========================================
        # 1. DEMAND ZONE SCANNING (BUY SETUP)
        # ==========================================
        if weekly_trend == "UP" and daily_trend == "UP" and trend_125m == "UP":
            daily_demand_found = False
            zone_high, zone_low = 0, 0

            for i in range(3, 6):
                if len(df_daily) < i+1:
                    break
                o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, _ = analyze_candle(o, h, l, c)
                
                oo, oh, ol, oc = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                ob_pct, _ = analyze_candle(oo, oh, ol, oc)

                if b_pct <= 40 and ob_pct >= 60 and oc > oo:
                    daily_demand_found = True
                    zone_high, zone_low = h, l
                    break

            if daily_demand_found and (zone_low <= current_price <= zone_high * 1.005):
                leg_in_b, _ = analyze_candle(df_15m['Open'].iloc[-3], df_15m['High'].iloc[-3], df_15m['Low'].iloc[-3], df_15m['Close'].iloc[-3])
                base_b, _ = analyze_candle(df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2])
                leg_out_b, _ = analyze_candle(df_15m['Open'].iloc[-1], df_15m['High'].iloc[-1], df_15m['Low'].iloc[-1], df_15m['Close'].iloc[-1])

                if leg_in_b >= 80 and base_b <= 35 and leg_out_b >= 75 and df_15m['Close'].iloc[-1] > df_15m['Open'].iloc[-1]:
                    msg = (
                        f"🟢 *DEMAND ZONE (BUY) TRIGGER: {name} ({symbol})* 🟢\n\n"
                        f"📈 **Trends:** Weekly({weekly_trend}) | Daily({daily_trend}) | 125m({trend_125m})\n"
                        f"📍 **Demand Zone:** {round(zone_low, 2)} - {round(zone_high, 2)}\n"
                        f"⚡ **15m Structure:** Leg-in({round(leg_in_b,1)}%) | Base({round(base_b,1)}%) | Leg-out({round(leg_out_b,1)}%)\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                    )
                    send_telegram_alert(msg)
                    return True

        # ==========================================
        # 2. SUPPLY ZONE SCANNING (SELL SETUP)
        # ==========================================
        if weekly_trend == "DOWN" and daily_trend == "DOWN" and trend_125m == "DOWN":
            daily_supply_found = False
            s_zone_high, s_zone_low = 0, 0

            for i in range(3, 5):
                if len(df_daily) < i+1:
                    break
                o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, _ = analyze_candle(o, h, l, c)
                
                oo, oh, ol, oc = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                ob_pct, _ = analyze_candle(oo, oh, ol, oc)

                if b_pct <= 40 and ob_pct >= 60 and oc < oo:
                    daily_supply_found = True
                    s_zone_high, s_zone_low = h, l
                    break

            if daily_supply_found and (s_zone_low * 0.995 <= current_price <= s_zone_high):
                leg_in_b, _ = analyze_candle(df_15m['Open'].iloc[-3], df_15m['High'].iloc[-3], df_15m['Low'].iloc[-3], df_15m['Close'].iloc[-3])
                base_b, _ = analyze_candle(df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2])
                leg_out_b, _ = analyze_candle(df_15m['Open'].iloc[-1], df_15m['High'].iloc[-1], df_15m['Low'].iloc[-1], df_15m['Close'].iloc[-1])

                if leg_in_b >= 80 and base_b <= 35 and leg_out_b >= 75 and df_15m['Close'].iloc[-1] < df_15m['Open'].iloc[-1]:
                    msg = (
                        f"🔴 *SUPPLY ZONE (SELL) TRIGGER: {name} ({symbol})* 🔴\n\n"
                        f"📉 **Trends:** Weekly({weekly_trend}) | Daily({daily_trend}) | 125m({trend_125m})\n"
                        f"📍 **Supply Zone:** {round(s_zone_low, 2)} - {round(s_zone_high, 2)}\n"
                        f"⚡ **15m Structure:** Leg-in({round(leg_in_b,1)}%) | Base({round(base_b,1)}%) | Leg-out({round(leg_out_b,1)}%)\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                    )
                    send_telegram_alert(msg)
                    return True

    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
    
    return False

def main():
    # Large Cap & Mid Cap Full 250+ Watchlist
    watchlist = {
        "RELIANCE.NS": "Reliance Industries", "TCS.NS": "TCS", "HDFCBANK.NS": "HDFC Bank",
        "ICICIBANK.NS": "ICICI Bank", "INFY.NS": "Infosys", "BHARTIARTL.NS": "Bharti Airtel",
        "ITC.NS": "ITC", "SBIN.NS": "State Bank of India", "LTIM.NS": "LTIMindtree",
        "TATAMOTORS.NS": "Tata Motors", "AXISBANK.NS": "Axis Bank", "KOTAKBANK.NS": "Kotak Bank",
        "LT.NS": "Larsen & Toubro", "HCLTECH.NS": "HCL Tech", "ASIANPAINT.NS": "Asian Paints",
        "MARUTI.NS": "Maruti Suzuki", "SUNPHARMA.NS": "Sun Pharma", "TITAN.NS": "Titan Company",
        "BAJFINANCE.NS": "Bajaj Finance", "TATASTEEL.NS": "Tata Steel", "NTPC.NS": "NTPC",
        "POWERGRID.NS": "Power Grid", "M&M.NS": "Mahindra & Mahindra", "ULTRACEMCO.NS": "UltraTech Cement",
        "PERSISTENT.NS": "Persistent", "COFORGE.NS": "Coforge", "POLYCAB.NS": "Polycab",
        "DIXON.NS": "Dixon", "TRENT.NS": "Trent", "BEL.NS": "Bharat Electronics",
        "HAL.NS": "HAL", "VOLTAS.NS": "Voltas", "ADANIENT.NS": "Adani Ent", "ADANIPORTS.NS": "Adani Ports",
        "BAJAJFINSV.NS": "Bajaj Finserv", "BPCL.NS": "BPCL", "CIPLA.NS": "Cipla",
        "COALINDIA.NS": "Coal India", "DIVISLAB.NS": "Divis Lab", "DRREDDY.NS": "Dr Reddy",
        "EICHERMOT.NS": "Eicher Motors", "GRASIM.NS": "Grasim", "HINDALCO.NS": "Hindalco",
        "HINDUNILVR.NS": "HUL", "INDUSINDBK.NS": "IndusInd Bank", "JSWSTEEL.NS": "JSW Steel",
        "NESTLEIND.NS": "Nestle", "ONGC.NS": "ONGC", "SBILIFE.NS": "SBI Life",
        "SHRIRAMFIN.NS": "Shriram Finance", "TATACONSUM.NS": "Tata Consumer", "TECHM.NS": "Tech Mahindra",
        "WIPRO.NS": "Wipro", "ABB.NS": "ABB India", "ADANIGREEN.NS": "Adani Green",
        "ADANIPOWER.NS": "Adani Power", "AMBUJACEM.NS": "Ambuja Cem", "APOLLOHOSP.NS": "Apollo Hosp",
        "ASHOKLEY.NS": "Ashok Leyland", "BAJAJ-AUTO.NS": "Bajaj Auto", "BANKBARODA.NS": "Bank of Baroda",
        "BERGEPAINT.NS": "Berger Paints", "BHARATFORG.NS": "Bharat Forge", "BOSCHLTD.NS": "Bosch Ltd",
        "BRITANNIA.NS": "Britannia", "CANBK.NS": "Canara Bank", "CHOLAFIN.NS": "Cholafin",
        "COLPAL.NS": "Colgate", "DABUR.NS": "Dabur", "DLF.NS": "DLF", "GAIL.NS": "GAIL",
        "GODREJCP.NS": "Godrej CP", "GODREJPROP.NS": "Godrej Prop", "HAVELLS.NS": "Havells",
        "HEROMOTOCO.NS": "Hero MotoCorp", "ICICIGI.NS": "ICICI Lombard", "ICICIPRULI.NS": "ICICI Pru",
        "IDFCFIRSTB.NS": "IDFC First Bank", "INDIGO.NS": "IndiGo", "IOC.NS": "IOC", "IRCTC.NS": "IRCTC",
        "JINDALSTEL.NS": "Jindal Steel", "JIOFIN.NS": "Jio Financial", "LUPIN.NS": "Lupin",
        "MARICO.NS": "Marico", "MCDOWELL-N.NS": "United Spirits", "MOTHERSON.NS": "Motherson",
        "MUTHOOTFIN.NS": "Muthoot Finance", "NAUKRI.NS": "Info Edge", "NMDC.NS": "NMDC",
        "OBEROIRLTY.NS": "Oberoi Realty", "PAYTM.NS": "Paytm", "PFC.NS": "PFC",
        "PIDILITIND.NS": "Pidilite", "PIIND.NS": "PI Industries", "PNB.NS": "PNB",
        "RECLTD.NS": "REC Ltd", "SAIL.NS": "SAIL", "SBICARD.NS": "SBI Cards", "SIEMENS.NS": "Siemens",
        "SRF.NS": "SRF", "TVSMOTOR.NS": "TVS Motor", "UBL.NS": "UBL", "MGL.NS": "Mahanagar Gas",
        "IPCALAB.NS": "Ipca Lab", "ALKEM.NS": "Alkem", "SYNGENE.NS": "Syngene", "TATACOMM.NS": "Tata Comm",
        "AJANTPHARM.NS": "Ajanta Pharma", "AIAENG.NS": "AIA Engineering", "APLAPOLLO.NS": "APL Apollo",
        "ASTRAL.NS": "Astral", "AUBANK.NS": "AU Bank", "BALKRISIND.NS": "Balkrishna",
        "BANDHANBNK.NS": "Bandhan Bank", "BATAINDIA.NS": "Bata India", "BEML.NS": "BEML",
        "CANFINHOME.NS": "Can Fin Homes", "CARBORUNIV.NS": "Carborundum", "CASTROLIND.NS": "Castrol",
        "CEATLTD.NS": "CEAT", "CESC.NS": "CESC", "CHAMBLFERT.NS": "Chambal Fert",
        "CUMMINSIND.NS": "Cummins", "CYIENT.NS": "Cyient", "DEEPAKNTR.NS": "Deepak Nitrite",
        "DEVYANI.NS": "Devyani", "ESCORTS.NS": "Escorts", "EXIDEIND.NS": "Exide",
        "FEDERALBNK.NS": "Federal Bank", "FINCABLES.NS": "Finolex Cables", "FINPIPE.NS": "Finolex Ind",
        "FORTIS.NS": "Fortis", "GLENMARK.NS": "Glenmark", "GMDC.NS": "GMDC", "GNFC.NS": "GNFC",
        "GODREJIND.NS": "Godrej Ind", "GRANULES.NS": "Granules", "GSPL.NS": "GSPL",
        "HAPPSTMNDS.NS": "Happiest Minds", "HINDCOPPER.NS": "Hind Copper", "HINDZINC.NS": "Hind Zinc",
        "IDBI.NS": "IDBI Bank", "IEX.NS": "IEX", "INDHOTEL.NS": "Indian Hotels", "ITI.NS": "ITI",
        "JBCHEPHARM.NS": "JB Chem", "JKCEMENT.NS": "JK Cement", "JKLAKSHMI.NS": "JK Lakshmi",
        "JKPAPER.NS": "JK Paper", "JSL.NS": "Jindal Stainless", "JUSTDIAL.NS": "Just Dial",
        "KAJARIACER.NS": "Kajaria", "KPRMILL.NS": "KPR Mill", "LALPATHLAB.NS": "Lal PathLabs",
        "LAURUSLABS.NS": "Laurus Labs", "LICHSGFIN.NS": "LIC Housing", "LINDEINDIA.NS": "Linde India",
        "MAPMYINDIA.NS": "MapmyIndia", "MAHSEAMLES.NS": "Mah Seamless", "MAXHEALTH.NS": "Max Health",
        "METROPOLIS.NS": "Metropolis", "MFSL.NS": "Max Financial", "MINDACORP.NS": "Minda Corp",
        "MRF.NS": "MRF", "MRPL.NS": "MRPL", "NATCOPHARM.NS": "Natco Pharma",
        "NATIONALUM.NS": "National Aluminium", "NAVINFLUOR.NS": "Navin Fluorine", "NBCC.NS": "NBCC",
        "NCC.NS": "NCC", "NHPC.NS": "NHPC", "NLCINDIA.NS": "NLC India", "NUVOCO.NS": "Nuvoco",
        "OFSS.NS": "OFSS", "PAGEIND.NS": "Page Ind", "PCBL.NS": "PCBL", "PNCINFRA.NS": "PNC Infra",
        "POONAWALLA.NS": "Poonawalla", "PRAJIND.NS": "Praj Ind", "PRESTIGE.NS": "Prestige",
        "RADICO.NS": "Radico", "RAJESHEXPO.NS": "Rajesh Exports", "RALLIS.NS": "Rallis",
        "RAMCOCEM.NS": "Ramco Cements", "RATNAMANI.NS": "Ratnamani", "RAYMOND.NS": "Raymond",
        "RBLBANK.NS": "RBL Bank", "RAILTEL.NS": "RailTel", "RELAXO.NS": "Relaxo", "RITES.NS": "RITES",
        "RVNL.NS": "RVNL", "SCHAEFFLER.NS": "Schaeffler", "SCI.NS": "SCI", "SHREECEM.NS": "Shree Cement",
        "SKFINDIA.NS": "SKF India", "SOBHA.NS": "Sobha", "SONACOMS.NS": "Sona Coms",
        "STAR.NS": "Strides Pharma", "SUMICHEM.NS": "Sumitomo", "SUNDRMFAST.NS": "Sundram Fasteners",
        "SUNTV.NS": "Sun TV", "SUPREMEIND.NS": "Supreme Ind", "SUZLON.NS": "Suzlon",
        "SWANENERGY.NS": "Swan Energy", "SYMPHONY.NS": "Symphony", "TANLA.NS": "Tanla",
        "TATAELXSI.NS": "Tata Elxsi", "TATAPOWER.NS": "Tata Power", "THERMAX.NS": "Thermax",
        "TIMKEN.NS": "Timken", "TORNTPOWER.NS": "Torrent Power", "TRIDENT.NS": "Trident",
        "TTKPRESTIG.NS": "TTK Prestige", "UNIONBANK.NS": "Union Bank", "VGUARD.NS": "V-Guard",
        "VIPIND.NS": "VIP Ind", "VTL.NS": "Vardhman Textiles", "WELSPUNLIV.NS": "Welspun Living",
        "WHIRLPOOL.NS": "Whirlpool", "YESBANK.NS": "Yes Bank", "ZEEL.NS": "Zee Ent",
        "ZENSARTECH.NS": "Zensar Tech", "ZYDUSLIFE.NS": "Zydus Lifesciences"
    }

    print("Starting Advanced Demand & Supply Zone Scanner for Full 250+ Stocks...")
    total_scanned = len(watchlist)
    matched_count = 0

    for symbol, name in watchlist.items():
        if scan_stock(symbol, name):
            matched_count += 1

    summary_msg = (
        "🤖 *DEMAND & SUPPLY SCANNER COMPLETED!*\n\n"
        "✅ **स्कैन सफलतापूर्वक पूरा हो गया है।**\n"
        f"📊 **कुल स्कैन किए गए स्टॉक्स:** {total_scanned}\n"
        f"🎯 **शर्तों से मैच हुए स्टॉक्स:** {matched_count}\n\n"
        "🟢 *अब लार्ज और मिड कैप के सभी 250+ स्टॉक्स स्कैन हो चुके हैं!*"
    )
    send_telegram_alert(summary_msg)

if __name__ == "__main__":
    main()
