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
        
        df_daily = ticker.history(period="3m", interval="1d")
        df_15m = ticker.history(period="5d", interval="15m")

        if df_daily.empty or df_15m.empty or len(df_daily) < 5 or len(df_15m) < 5:
            return False

        current_price = df_daily['Close'].iloc[-1]
        triggered = False

        # =========================================================
        # 1. PURE DEMAND ZONE CHECK (BULLISH)
        # =========================================================
        daily_dz_found = False
        dz_high, dz_low = 0, 0

        # Daily Zone: 3 or 4 candles back
        for i in range(3, 5):
            o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
            b_pct, w_pct = analyze_candle(o, h, l, c)
            
            out_o, out_h, out_l, out_c = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
            out_b, out_w = analyze_candle(out_o, out_h, out_l, out_c)

            # Base candle body <= 30%, wick >= 70% AND Leg-out green body >= 90%, wick <= 10%
            if b_pct <= 30 and w_pct >= 70 and out_b >= 90 and out_w <= 10 and out_c > out_o:
                daily_dz_found = True
                dz_high, dz_low = h, l
                break

        if daily_dz_found and (dz_low <= current_price <= dz_high * 1.01):
            # 15-Min Execution: Check 1 or 2 candles back near daily zone
            for j in range(1, 3):
                idx = -j
                if abs(len(df_15m) + idx) < 3:
                    continue
                
                in_o, in_h, in_l, in_c = df_15m['Open'].iloc[idx-2], df_15m['High'].iloc[idx-2], df_15m['Low'].iloc[idx-2], df_15m['Close'].iloc[idx-2]
                b_in, w_in = analyze_candle(in_o, in_h, in_l, in_c)

                base_o, base_h, base_l, base_c = df_15m['Open'].iloc[idx-1], df_15m['High'].iloc[idx-1], df_15m['Low'].iloc[idx-1], df_15m['Close'].iloc[idx-1]
                b_base, w_base = analyze_candle(base_o, base_h, base_l, base_c)

                out_o1, out_h1, out_l1, out_c1 = df_15m['Open'].iloc[idx], df_15m['High'].iloc[idx], df_15m['Low'].iloc[idx], df_15m['Close'].iloc[idx]
                b_out, w_out = analyze_candle(out_o1, out_h1, out_l1, out_c1)

                # Rules: Leg-in (>=90% body, <=10% wick), Base (<=30% body, >=70% wick), Leg-out Green (>=90% body, <=10% wick)
                valid_in = b_in >= 90 and w_in <= 10
                valid_base = b_base <= 30 and w_base >= 70
                valid_out = b_out >= 90 and w_out <= 10 and out_c1 > out_o1

                if valid_in and valid_base and valid_out:
                    msg = (
                        f"🔥 *PURE DEMAND ZONE TRIGGER: {name} ({symbol})* 🔥\n\n"
                        f"📍 **Daily Demand Zone:** {round(dz_low, 2)} - {round(dz_high, 2)}\n"
                        f"⚡ **15-Min Structure Matched:**\n"
                        f"• Leg-in Body: {round(b_in, 1)}% (Wick: {round(w_in, 1)}%)\n"
                        f"• Base Body: {round(b_base, 1)}% (Wick: {round(w_base, 1)}%)\n"
                        f"• Leg-out Body (Green): {round(b_out, 1)}% (Wick: {round(w_out, 1)}%)\n\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                        "✅ *Pure Price Action Setup Complete!*"
                    )
                    send_telegram_alert(msg)
                    triggered = True
                    break

        # =========================================================
        # 2. PURE SUPPLY ZONE CHECK (BEARISH)
        # =========================================================
        daily_sz_found = False
        sz_high, sz_low = 0, 0

        # Daily Zone: 3 or 4 candles back
        for i in range(3, 5):
            o, h, l, c = df_daily['Open'].iloc[-i], df_daily['High'].iloc[-i], df_daily['Low'].iloc[-i], df_daily['Close'].iloc[-i]
            b_pct, w_pct = analyze_candle(o, h, l, c)
            
            out_o, out_h, out_l, out_c = df_daily['Open'].iloc[-i+1], df_daily['High'].iloc[-i+1], df_daily['Low'].iloc[-i+1], df_daily['Close'].iloc[-i+1]
            out_b, out_w = analyze_candle(out_o, out_h, out_l, out_c)

            # Base candle body <= 30%, wick >= 70% AND Leg-out Red body >= 90%, wick <= 10%
            if b_pct <= 30 and w_pct >= 70 and out_b >= 90 and out_w <= 10 and out_c < out_o:
                daily_sz_found = True
                sz_high, sz_low = h, l
                break

        if daily_sz_found and (sz_low * 0.99 <= current_price <= sz_high):
            # 15-Min Execution: Check 1 or 2 candles back near daily zone
            for j in range(1, 3):
                idx = -j
                if abs(len(df_15m) + idx) < 3:
                    continue
                
                in_o, in_h, in_l, in_c = df_15m['Open'].iloc[idx-2], df_15m['High'].iloc[idx-2], df_15m['Low'].iloc[idx-2], df_15m['Close'].iloc[idx-2]
                b_in, w_in = analyze_candle(in_o, in_h, in_l, in_c)

                base_o, base_h, base_l, base_c = df_15m['Open'].iloc[idx-1], df_15m['High'].iloc[idx-1], df_15m['Low'].iloc[idx-1], df_15m['Close'].iloc[idx-1]
                b_base, w_base = analyze_candle(base_o, base_h, base_l, base_c)

                out_o1, out_h1, out_l1, out_c1 = df_15m['Open'].iloc[idx], df_15m['High'].iloc[idx], df_15m['Low'].iloc[idx], df_15m['Close'].iloc[idx]
                b_out, w_out = analyze_candle(out_o1, out_h1, out_l1, out_c1)

                # Rules: Leg-in (>=90% body, <=10% wick), Base (<=30% body, >=70% wick), Leg-out Red (>=90% body, <=10% wick)
                valid_in = b_in >= 90 and w_in <= 10
                valid_base = b_base <= 30 and w_base >= 70
                valid_out = b_out >= 90 and w_out <= 10 and out_c1 < out_o1

                if valid_in and valid_base and valid_out:
                    msg = (
                        f"🔻 *PURE SUPPLY ZONE TRIGGER: {name} ({symbol})* 🔻\n\n"
                        f"📍 **Daily Supply Zone:** {round(sz_low, 2)} - {round(sz_high, 2)}\n"
                        f"⚡ **15-Min Structure Matched:**\n"
                        f"• Leg-in Body: {round(b_in, 1)}% (Wick: {round(w_in, 1)}%)\n"
                        f"• Base Body: {round(b_base, 1)}% (Wick: {round(w_base, 1)}%)\n"
                        f"• Leg-out Body (Red): {round(b_out, 1)}% (Wick: {round(w_out, 1)}%)\n\n"
                        f"🎯 **Current Price:** ₹{round(current_price, 2)}\n"
                        "✅ *Pure Price Action Setup Complete!*"
                    )
                    send_telegram_alert(msg)
                    triggered = True
                    break

        return triggered

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

    print("Starting Pure Action Zone Scan (No EMA)...")
    total_scanned = len(watchlist)
    matched_count = 0

    for symbol, name in watchlist.items():
        if scan_stock(symbol, name):
            matched_count += 1

    summary_msg = (
        "🤖 *PURE PRICE ACTION SCANNER COMPLETED!*\n\n"
        f"📊 **Scanned Stocks:** {total_scanned}\n"
        f"🎯 **Triggered Setups:** {matched_count}\n\n"
        "✅ *No EMA, Only Pure Daily & 15-Min Zone Match!*"
    )
    send_telegram_alert(summary_msg)

if __name__ == "__main__":
    main()
