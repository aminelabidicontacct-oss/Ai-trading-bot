import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
from streamlit_autorefresh import st_autorefresh
import requests

# =========================
# AUTO REFRESH (IMPORTANT)
# =========================
st_autorefresh(interval=5000, key="refresh")

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI Trading Dashboard")

# =========================
# MODEL
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
# COINS + TF
# =========================
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}

coin = st.selectbox("📌 Coin", COINS)
tf = st.selectbox("⏱️ Timeframe", list(TF_MAP.keys()))
timeframe = TF_MAP[tf]

# =========================
# SAFE PRICE FUNCTION
# =========================
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        r = requests.get(url, timeout=3).json()
        return float(r["price"])
    except:
        try:
            return float(exchange.fetch_ticker(f"{symbol}/USDT")["last"])
        except:
            return None

# =========================
# DATA
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
# UI
# =========================
st.subheader("💰 Live Prices")

price_cols = st.columns(len(COINS))
price_boxes = {}

for i, c in enumerate(COINS):
    price_boxes[c] = price_cols[i].empty()

signal_box = st.empty()

# =========================
# LIVE UPDATE (
