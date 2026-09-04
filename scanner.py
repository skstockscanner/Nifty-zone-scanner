import os
import time
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

        if df_weekly.empty or df_daily.empty:
            return False

        weekly_trend = get_simple_trend(df_weekly)

        # ==========================================
        # 1. DEMAND ZONE SCANNING (BUY SETUP)
        # ==========================================
        if weekly_trend == "UP":
            for i in range(3, 5):  # 3 से 4 कैंडल पीछे
                if len(df_daily) < i + 1:
                    break
                
                # Base Candle (i index पर) -> Body <= 30%, Wick >= 70%
                o_base, h_base, l_base, c_base = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, w_pct = analyze_candle(o_base, h_base, l_base, c_base)
                
                # Leg-out / Strong Green Candle (उसके तुरंत बाद वाली कैंडल i-1 index पर) -> Body >= 90%, Wick <= 10%
                o_leg, h_leg, l_leg, c_leg = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                leg_b_pct, leg_w_pct = analyze_candle(o_leg, h_leg, l_leg, c_leg)

                if b_pct <= 30 and w_pct >= 70 and leg_b_pct >= 90 and leg_w_pct <= 10 and c_leg > o_leg:
                    zone_high, zone_low = h_base, l_base
                    msg = (
                        f"🟢 *DEMAND ZONE FORMED: {name} ({symbol})* 🟢\n\n"
                        f"📈 **Weekly Trend:** {weekly_trend}\n"
                        f"📍 **Demand Zone (3-4 Candles Back):** ₹{round(zone_low, 2)} - ₹{round(zone_high, 2)}\n"
                        f"⏳ **Position:** {i} candles ago\n"
                    )
                    send_telegram_alert(msg)
                    return True

        # ==========================================
        # 2. SUPPLY ZONE SCANNING (SELL SETUP)
        # ==========================================
        if weekly_trend == "DOWN":
            for i in range(3, 5):  # 3 से 4 कैंडल पीछे
                if len(df_daily) < i + 1:
                    break
                
                # Base Candle (i index पर) -> Body <= 30%, Wick >= 70%
                o_base, h_base, l_base, c_base = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
                b_pct, w_pct = analyze_candle(o_base, h_base, l_base, c_base)
                
                # Leg-out / Strong Red Candle (उसके तुरंत बाद वाली कैंडल i-1 index पर) -> Body >= 90%, Wick <= 10%
                o_leg, h_leg, l_leg, c_leg = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
                leg_b_pct, leg_w_pct = analyze_candle(o_leg, h_leg, l_leg, c_leg)

                if b_pct <= 30 and w_pct >= 70 and leg_b_pct >= 90 and leg_w_pct <= 10 and c_leg < o_leg:
                    s_zone_high, s_zone_low = h_base, l_base
                    msg = (
                        f"🔴 *SUPPLY ZONE FORMED: {name} ({symbol})* 🔴\n\n"
                        f"📉 **Weekly Trend:** {weekly_trend}\n"
                        f"📍 **Supply Zone (3-4 Candles Back):** ₹{round(s_zone_low, 2)} - ₹{round(s_zone_high, 2)}\n"
                        f"⏳ **Position:** {i} candles ago\n"
                    )
                    send_telegram_alert(msg)
                    return True

    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
    
    return False

def main():
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
        "DEVYANI.NS": "Devyani",
        "ESCORTS.NS": "Escorts Kubota", "EXIDEIND.NS": "Exide Industries",
        "FEDERALBNK.NS": "Federal Bank", "FINCABLES.NS": "Finolex Cables", "FINPIPE.NS": "Finolex Industries",
        "FORTIS.NS": "Fortis Healthcare", "GLENMARK.NS": "Glenmark Pharma", "GMDC.NS": "Gujarat Mineral",
        "GNFC.NS": "GNFC", "GODREJIND.NS": "Godrej Industries", "GRANULES.NS": "Granules India",
        "GSPL.NS": "Gujarat State Petronet", "HAPPSTMNDS.NS": "Happiest Minds", "HINDCOPPER.NS": "Hindustan Copper",
        "HINDZINC.NS": "Hindustan Zinc", "IDBI.NS": "IDBI Bank", "IEX.NS": "Indian Energy Exchange",
        "INDHOTEL.NS": "Indian Hotels", "ITI.NS": "ITI Ltd", "JBCHEPHARM.NS": "JB Chemicals",
        "JKCEMENT.NS": "JK Cement", "JKLAKSHMI.NS": "JK Lakshmi Cement", "JKPAPER.NS": "JK Paper",
        "JSL.NS": "Jindal Stainless", "JUSTDIAL.NS": "Just Dial", "KAJARIACER.NS": "Kajaria Ceramics",
        "KPRMILL.NS": "KPR Mill", "LALPATHLAB.NS": "Dr. Lal PathLabs", "LAURUSLABS.NS": "Laurus Labs",
        "LICHSGFIN.NS": "LIC Housing Finance", "LINDEINDIA.NS": "Linde India", "MAPMYINDIA.NS": "CE Info Systems",
        "MAHSEAMLES.NS": "Maharashtra Seamless", "MAXHEALTH.NS": "Max Healthcare", "METROPOLIS.NS": "Metropolis Healthcare",
        "MFSL.NS": "Max Financial", "MINDACORP.NS": "Minda Corp", "MRF.NS": "MRF",
        "MRPL.NS": "MRPL", "NATCOPHARM.NS": "Natco Pharma", "NATIONALUM.NS": "National Aluminium",
        "NAVINFLUOR.NS": "Navin Fluorine", "NBCC.NS": "NBCC", "NCC.NS": "NCC",
        "NHPC.NS": "NHPC", "NLCINDIA.NS": "NLC India", "NUVOCO.NS": "Nuvoco Vistas",
        "OFSS.NS": "Oracle Financial", "PAGEIND.NS": "Page Industries", "PCBL.NS": "PCBL",
        "PNCINFRA.NS": "PNC Infratech", "POONAWALLA.NS": "Poonawalla Fincorp", "PRAJIND.NS": "Praj Industries",
        "PRESTIGE.NS": "Prestige Estates", "RADICO.NS": "Radico Khaitan", "RAJESHEXPO.NS": "Rajesh Exports",
        "RALLIS.NS": "Rallis India", "RAMCOCEM.NS": "Ramco Cements", "RATNAMANI.NS": "Ratnamani Metals",
        "RAYMOND.NS": "Raymond", "RBLBANK.NS": "RBL Bank", "RAILTEL.NS": "RailTel Corporation",
        "RELAXO.NS": "Relaxo Footwears", "RITES.NS": "RITES", "RVNL.NS": "Rail Vikas Nigam",
        "SCHAEFFLER.NS": "Schaeffler India", "SCI.NS": "Shipping Corporation", "SHREECEM.NS": "Shree Cement",
        "SKFINDIA.NS": "SKF India", "SOBHA.NS": "Sobha", "SONACOMS.NS": "Sona BLW",
        "STAR.NS": "Strides Pharma", "SUMICHEM.NS": "Sumitomo Chemical", "SUNDRMFAST.NS": "Sundram Fasteners",
        "SUNTV.NS": "Sun TV Network", "SUPREMEIND.NS": "Supreme Industries", "SUZLON.NS": "Suzlon Energy",
        "SWANENERGY.NS": "Swan Energy", "SYMPHONY.NS": "Symphony", "TANLA.NS": "Tanla Platforms",
        "TATAELXSI.NS": "Tata Elxsi", "TATAPOWER.NS": "Tata Power", "THERMAX.NS": "Thermax",
        "TIMKEN.NS": "Timken India", "TORNTPOWER.NS": "Torrent Power", "TRIDENT.NS": "Trident",
        "TTKPRESTIG.NS": "TTK Prestige", "UNIONBANK.NS": "Union Bank of India", "VGUARD.NS": "V-Guard Industries",
        "VIPIND.NS": "VIP Industries", "VTL.NS": "Vardhman Textiles", "WELSPUNLIV.NS": "Welspun Living",
        "WHIRLPOOL.NS": "Whirlpool of India", "YESBANK.NS": "Yes Bank", "ZEEL.NS": "Zee Entertainment",
        "ZENSARTECH.NS": "Zensar Technologies", "ZYDUSLIFE.NS": "Zydus Lifesciences"
    }

    print("Starting Full 250+ Stock Zone Scanner...")
    total_scanned = len(watchlist)
    matched_count = 0

    for symbol, name in watchlist.items():
        if scan_stock(symbol, name):
            matched_count += 1
        
        # हर स्टॉक के स्कैन के बीच 1 सेकंड का गैप
        time.sleep(1)

    summary_msg = (
        "🤖 *ZONE SCANNER COMPLETED!*\n\n"
        f"📊 **कुल स्कैन किए गए स्टॉक्स:** {total_scanned}\n"
        f"🎯 **शर्तों से मैच हुए स्टॉक्स:** {matched_count}"
    )
    send_telegram_alert(summary_msg)

if __name__ == "__main__":
    main()
