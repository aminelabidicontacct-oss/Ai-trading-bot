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
# PRICE API (FAST + SAFE)
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
# CANDLE DATA
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
# UI SETTINGS
# =========================
coins = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]

mapping = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "ANKR": "ankr",
    "SUI": "sui"
}

timeframes = {
    "1D": "1d",
    "4H": "4h",
    "1H": "1h",
    "15M": "15m"
}

symbol = st.selectbox("📌 Select Coin", coins)

# =========================
# LIVE PRICES
# =========================
st.subheader("💰 Live Prices")

prices = get_all_prices()

cols = st.columns(len(coins))

for i, c in enumerate(coins):
    coin_id = mapping.get(c)
    price = prices.get(coin_id, {}).get("usd")

    if price:
        cols[i].metric(c, f"${price:,.4f}")
    else:
        cols[i].metric(c, "—")

# =========================
# ANALYSIS
# =========================
st.subheader(f"📈 Signal Analysis: {symbol}")

signals = {}

for tf_name, tf_value in timeframes.items():

    df = get_data(symbol, tf_value)

    if df is None or len(df) == 0:
        continue

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

    if buy > 0.7:
        signal = "🟢 BUY"
    elif sell > 0.7:
        signal = "🔴 SELL"
    else:
        signal = "⚪ WAIT"

    signals[tf_name] = signal

    st.write(f"**{tf_name}:** {signal} ({buy:.2f}/{sell:.2f})")

# =========================
# FINAL DECISION
# =========================
st.subheader("🎯 FINAL DECISION")

buy_count = list(signals.values()).count("🟢 BUY")
sell_count = list(signals.values()).count("🔴 SELL")

if signals.get("1D") == "🟢 BUY" and buy_count >= 2:
    st.success("🟢 STRONG LONG TERM BUY")
elif signals.get("1D") == "🔴 SELL" and sell_count >= 2:
    st.error("🔴 STRONG LONG TERM SELL")
else:
    st.warning("⚪ NO CLEAR SIGNAL")
