import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
from streamlit_autorefresh import st_autorefresh

# =========================
# AUTO REFRESH (SMART)
# =========================
st_autorefresh(interval=15000, key="refresh")  # كل 15 ثانية

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI PRO Swing Trading Dashboard")

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
TF_MAP = {
    "1D": "1d",
    "4H": "4h",
    "1H": "1h",
    "15M": "15m"
}

coin = st.selectbox("📌 Coin", COINS)
tf = st.selectbox("⏱️ Timeframe", list(TF_MAP.keys()))
timeframe = TF_MAP[tf]

# =========================
# FETCH DATA
# =========================
@st.cache_data(ttl=10)
def get_data(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=200)

        df = pd.DataFrame(bars, columns=[
            "time","open","high","low","close","volume"
        ])

        df["close"] = df["close"].astype(float)

        # indicators
        df["rsi"] = ta.momentum.rsi(df["close"], 14)
        df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
        df["ema200"] = ta.trend.ema_indicator(df["close"], 200)
        df["return"] = df["close"].pct_change()
        df["volatility"] = df["close"].rolling(10).std()

        df = df.dropna()
        return df

    except:
        return None

# =========================
# LIVE PRICES (FAST)
# =========================
st.subheader("💰 Live Prices")

price_cols = st.columns(len(COINS))

for i, c in enumerate(COINS):
    try:
        ticker = exchange.fetch_ticker(f"{c}/USDT")
        price_cols[i].metric(c, f"${ticker['last']:.2f}")
    except:
        price_cols[i].metric(c, "—")

# =========================
# AI ANALYSIS
# =========================
st.subheader("📈 AI Signal")

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

    st.markdown(f"""
    ## {signal}
    **Confidence:** {buy:.2%}

    💰 Price: `{price:.2f}`  
    🎯 Entry: `{entry:.2f}`  
    🚀 Target: `{target:.2f}`  
    ❌ Stop Loss: `{stop:.2f}`
    """)

else:
    st.warning("No data available")
