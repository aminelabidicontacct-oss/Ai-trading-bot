import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import time

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# LANGUAGES
# =========================
languages = {
    "English": {
        "title": "📊 AI PRO Swing Dashboard",
        "coin": "📌 Coin",
        "tf": "⏱️ Timeframe",
        "price": "💰 Live Prices",
        "signal": "📈 AI Signal"
    },
    "Arabic": {
        "title": "📊 لوحة التداول الاحترافية",
        "coin": "📌 العملة",
        "tf": "⏱️ الفريم",
        "price": "💰 الأسعار",
        "signal": "📈 الإشارة"
    }
}

lang = st.sidebar.selectbox("Language", list(languages.keys()))
t = languages[lang]

st.title(t["title"])

# =========================
# LOAD MODEL
# =========================
@st.cache_resource
def load_model():
    return joblib.load("ai_trading_model.pkl")

model = load_model()

# =========================
# EXCHANGE
# =========================
exchange = ccxt.kucoin({'enableRateLimit': True})

# =========================
# SETTINGS
# =========================
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}

coin = st.sidebar.selectbox(t["coin"], COINS)
tf = st.sidebar.selectbox(t["tf"], list(TF_MAP.keys()))
timeframe = TF_MAP[tf]

# =========================
# FETCH DATA (CACHED)
# =========================
@st.cache_data(ttl=10)
def get_data(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=200)

        df = pd.DataFrame(bars, columns=[
            "time","open","high","low","close","volume"
        ])

        df["close"] = df["close"].astype(float)

        df["rsi"] = ta.momentum.rsi(df["close"], 14)
        df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
        df["ema200"] = ta.trend.ema_indicator(df["close"], 200)
        df["return"] = df["close"].pct_change()
        df["volatility"] = df["close"].rolling(10).std()

        return df.dropna()

    except:
        return None

# =========================
# LIVE PRICES (SMOOTH UI)
# =========================
st.subheader(t["price"])

price_boxes = {}
cols = st.columns(len(COINS))

for i, c in enumerate(COINS):
    price_boxes[c] = cols[i].empty()

# =========================
# SIGNAL AREA
# =========================
signal_box = st.empty()

# =========================
# MAIN LOOP (NO FULL REFRESH)
# =========================
while True:

    # -------- LIVE PRICES --------
    for c in COINS:
        try:
            ticker = exchange.fetch_ticker(f"{c}/USDT")
            price_boxes[c].metric(c, f"${ticker['last']:.2f}")
        except:
            price_boxes[c].metric(c, "—")

    # -------- AI ANALYSIS --------
    df = get_data(coin, timeframe)

    if df is not None and model:

        last = df.iloc[-1]

        features = [[
            last["rsi"],
            last["ema50"],
            last["ema200"],
            last["return"],
            last["volatility"]
        ]]

        proba = model.predict_proba(features)[0]
        buy, sell = proba[1], proba[0]

        price = last["close"]
        entry = last["ema50"]
        target = entry * 1.12
        stop = entry * 0.97

        if buy > 0.7:
            signal = "🟢 BUY"
        elif sell > 0.7:
            signal = "🔴 SELL"
        else:
            signal = "⚪ WAIT"

        signal_box.markdown(f"""
        ## {t['signal']}
        ### {signal}

        💰 Price: `{price:.2f}`  
        🎯 Entry: `{entry:.2f}`  
        🚀 Target: `{target:.2f}`  
        ❌ Stop: `{stop:.2f}`  
        """)

    time.sleep(2)
