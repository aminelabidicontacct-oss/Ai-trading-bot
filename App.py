import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import time

# ==========================================
# 1. CONFIGURATION & MULTI-LANGUAGE
# ==========================================
st.set_page_config(layout="wide", page_title="Swing Signal Pro")

# Language Dictionary in Sidebar
translations = {
    "English": {
        "title": "⚡ AI Swing Signals",
        "coin": "Asset",
        "tf": "Timeframe",
        "price": "Market Prices",
        "entry": "Entry Point",
        "tp": "Take Profit (Target)",
        "sl": "Stop Loss",
        "signal": "AI Signal Strength"
    },
    "Arabic": {
        "title": "⚡ إشارات السوينج اليومية",
        "coin": "العملة",
        "tf": "الفريم",
        "price": "أسعار السوق",
        "entry": "نقطة الدخول",
        "tp": "الهدف (جني الأرباح)",
        "sl": "وقف الخسارة",
        "signal": "قوة الإشارة"
    },
    "French": {
        "title": "⚡ Signaux Swing IA",
        "coin": "Actif",
        "tf": "Unité de Temps",
        "price": "Prix du Marché",
        "entry": "Point d'Entrée",
        "tp": "Objectif (TP)",
        "sl": "Stop Loss",
        "signal": "Force du Signal"
    }
}

# --- SIDEBAR CONTROL ---
st.sidebar.header("Control Panel")
selected_lang = st.sidebar.selectbox("🌐 Language", list(translations.keys()), index=0)
t = translations[selected_lang]

@st.cache_resource
def load_model():
    try:
        return joblib.load("ai_trading_model.pkl")
    except:
        return None

model = load_model()
exchange = ccxt.kucoin({'enableRateLimit': True})

COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"4H (Swing)": "4h", "1H (Intraday)": "1h", "15M (Scalp)": "15m"}

st.sidebar.divider()
coin = st.sidebar.selectbox(t["coin"], COINS)
tf_name = st.sidebar.selectbox(t["tf"], list(TF_MAP.keys()), index=1)
timeframe = TF_MAP[tf_name]

# Placeholder for Trade Card in Sidebar
trade_card = st.sidebar.empty()

# ==========================================
# 2. CORE TRADING LOGIC
# ==========================================
def get_market_data(symbol, tf):
    try:
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=tf, limit=200)
        df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "vol"])
        
        # Technical indicators for the model
        df["rsi"] = ta.momentum.rsi(df["close"], 14)
        df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
        df["ema200"] = ta.trend.ema_indicator(df["close"], 200)
        df["return"] = df["close"].pct_change()
        df["volatility"] = df["close"].rolling(10).std()
        
        # ATR for dynamic Stop Loss and Target
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
        
        return df.dropna().iloc[-1]
    except:
        return None

# ==========================================
# 3. DASHBOARD UI
# ==========================================
st.title(t["title"])
st.subheader(t["price"])
price_cols = st.columns(len(COINS))
placeholders = [col.empty() for col in price_cols]

st.divider()
main_signal = st.empty()

# ==========================================
# 4. LIVE EXECUTION
# ==========================================
while True:
    # Update Live Prices Header
    for i, c in enumerate(COINS):
        try:
            ticker = exchange.fetch_ticker(f"{c}/USDT")
            placeholders[i].metric(c, f"${ticker['last']:.4f}")
        except:
            placeholders[i].metric(c, "N/A")

    # Generate Trade Setup
    data = get_market_data(coin, timeframe)
    
    if model and data is not None:
        features = [[data["rsi"], data["ema50"], data["ema200"], data["return"], data["volatility"]]]
        confidence = model.predict_proba(features)[0][1]
        
        # --- Trade Geometry ---
        curr_price = data["close"]
        atr = data["atr"]
        
        # Entry: Near EMA50 or Current if strong trend
        entry = data["ema50"] if curr_price > data["ema50"] else curr_price
        
        # Dynamic TP/SL using ATR (Volatility-based)
        stop_loss = entry - (atr * 1.5)
        take_profit = entry + (atr * 3.0) # Risk/Reward 1:2
        
        # UI Updates
        color = "#00ff00" if confidence > 0.7 else "#ff0000" if confidence < 0.3 else "#ffaa00"
        
        # Sidebar Trade Card
        trade_card.markdown(f"""
        ### 📋 Trade Setup
        ---
        **{t['entry']}:** `${entry:.4f}`
        **{t['tp']}:** `${take_profit:.4f}`
        **{t['sl']}:** `${stop_loss:.4f}`
        """)
        
        # Main Dashboard Signal
        main_signal.markdown(f"""
        <div style="padding:40px; border-radius:15px; border: 4px solid {color}; text-align:center; background-color:#111111;">
            <h1 style="color:{color}; font-size:60px; margin:0;">{confidence:.1%}</h1>
            <p style="color:white; font-size:24px;">{t['signal']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    time.sleep(15)
