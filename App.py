import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import time

# ==========================================
# 1. CONFIGURATION & LANGUAGES
# ==========================================
st.set_page_config(layout="wide", page_title="AI Swing Trader - Kucoin")

# Translation Dictionary
translations = {
    "English": {
        "title": "📊 AI Swing Trading Dashboard",
        "coin": "📌 Select Coin",
        "tf": "⏱️ Select Timeframe",
        "price": "💰 Live Market Prices",
        "entry": "🎯 Swing Entry Zone",
        "target": "🚀 Swing Target",
        "signal": "📈 AI Analysis Signal",
        "lang": "🌐 Interface Language"
    },
    "Arabic": {
        "title": "📊 لوحة تحكم التداول بنظام السوينج",
        "coin": "📌 اختر العملة",
        "tf": "⏱️ اختر الفريم الزمني",
        "price": "💰 أسعار السوق الحالية",
        "entry": "🎯 منطقة دخول السوينج",
        "target": "🚀 هدف السوينج",
        "signal": "📈 إشارة تحليل الذكاء الاصطناعي",
        "lang": "🌐 لغة الواجهة"
    },
    "French": {
        "title": "📊 Tableau de Bord Swing Trading IA",
        "coin": "📌 Choisir la Crypto",
        "tf": "⏱️ Choisir l'Unité de Temps",
        "price": "💰 Prix du Marché en Direct",
        "entry": "🎯 Zone d'Entrée Swing",
        "target": "🚀 Objectif Swing",
        "signal": "📈 Signal d'Analyse IA",
        "lang": "🌐 Langue de l'Interface"
    }
}

# --- SIDEBAR SETUP ---
st.sidebar.header("🛠️ Bot Settings")

# Language Selection
selected_lang = st.sidebar.selectbox("Language / اللغة / Langue", list(translations.keys()), index=0)
t = translations[selected_lang]

# AI Model Loader
@st.cache_resource
def load_model():
    try:
        return joblib.load("ai_trading_model.pkl")
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

model = load_model()
exchange = ccxt.kucoin({'enableRateLimit': True})

# Assets and Timeframes
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"1 Day": "1d", "4 Hours": "4h", "1 Hour": "1h", "15 Minutes": "15m"}

st.sidebar.divider()
selected_symbol = st.sidebar.selectbox(t["coin"], COINS)
selected_tf_name = st.sidebar.selectbox(t["tf"], list(TF_MAP.keys()), index=2)
selected_tf_val = TF_MAP[selected_tf_name]

# Placeholder for sidebar targets
entry_placeholder = st.sidebar.empty()

# ==========================================
# 2. DATA PROCESSING (STRICT ENGLISH)
# ==========================================
def fetch_and_analyze(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Technical Indicators
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(10).std()
        
        return df.dropna().iloc[-1], df
    except Exception:
        return None, None

# ==========================================
# 3. MAIN DASHBOARD UI
# ==========================================
st.title(t["title"])

st.subheader(t["price"])
price_cols = st.columns(len(COINS))
price_placeholders = [col.empty() for col in price_cols]

st.divider()
signal_placeholder = st.empty()

# ==========================================
# 4. EXECUTION LOOP
# ==========================================
while True:
    # A. Update Live Prices
    for i, coin in enumerate(COINS):
        try:
            ticker = exchange.fetch_ticker(f"{coin}/USDT")
            price_placeholders[i].metric(coin, f"${ticker['last']:.4f}")
        except:
            price_placeholders[i].metric(coin, "N/A")

    # B. AI Logic & Signal Generation
    last_data, full_df = fetch_and_analyze(selected_symbol, selected_tf_val)
    
    if model and last_data is not None:
        features = [[
            last_data['rsi'], last_data['ema50'], last_data['ema200'], 
            last_data['return'], last_data['volatility']
        ]]
        
        proba = model.predict_proba(features)[0]
        buy_score = proba[1]
        current_price = last_data['close']

        # Swing Trading Entry/Exit Logic
        # Target is set to a standard 12% swing profit
        entry_price = last_data['ema50'] if current_price > last_data['ema50'] else current_price * 0.985
        swing_target = entry_price * 1.12 
        
        # Signal Colors
        if buy_score > 0.7:
            status_text, color = "🟢 BUY", "#00ff00"
        elif buy_score < 0.3:
            status_text, color = "🔴 SELL", "#ff0000"
        else:
            status_text, color = "⚪ NEUTRAL", "#808080"

        signal_placeholder.markdown(
            f"<div style='padding:30px; border-radius:15px; border: 3px solid {color}; text-align:center; background-color:#111111;'>"
            f"<h1 style='color:{color}; margin:0;'>{status_text}</h1>"
            f"<h3>Confidence Score: {buy_score:.2%}</h3>"
            f"</div>", unsafe_allow_html=True
        )

        # Update Sidebar Targets
        entry_placeholder.markdown(
            f"--- \n"
            f"### {t['entry']}\n"
            f"## `${entry_price:.4f}` \n\n"
            f"### {t['target']}\n"
            f"## `${swing_target:.4f}`"
        )

    time.sleep(15)
    
