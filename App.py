import streamlit as st
import joblib
import requests
import pandas as pd
import ta

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI Professional Trading Dashboard")

model = joblib.load("ai_trading_model.pkl")

# =========================
# FAST PRICE LAYER (BATCH + CACHE)
# =========================
@st.cache_data(ttl=15)
def get_all_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"

        ids = "bitcoin,ethereum,solana,binancecoin,ankr,sui"

        r = requests.get(
            url,
            params={"ids": ids, "vs_currencies": "usd"},
            timeout=10
        )

        return r.json()

    except:
        return {}

# =========================
# CANDLE DATA (Binance)
# =========================
def get_data(symbol, interval):
    try:
        url = "https://api.binance.com/api/v3/klines"

        r = requests.get(
            url,
            params={
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "limit": 200
            },
            timeout=10
        )

        data = r.json()

        if not isinstance(data, list):
            return None

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
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
# UI
# =========================
coins = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]

mapping = {
    "BTC": "bitcoin",
    "
