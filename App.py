import streamlit as st
import joblib
import requests
import pandas as pd
import ta
import time

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI Trading Pro Dashboard")

model = joblib.load("ai_trading_model.pkl")

# =========================
# COINS
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

# =========================
# LIVE PRICE (FAST BINANCE)
# =========================
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        r = requests.get(url, timeout=5).json()
        return float(r["price"])
    except:
        return None

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

        if not isinstance(data, list) or len(data) < 50:
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
# TIMEFRAMES
# =========================
timeframes = {
    "1D": "1d",
    "4H": "4h",
    "1H": "1h",
    "15M": "15m"
}

symbol = st.selectbox("📌 Select Coin", coins)

# =========================
# LIVE PRICE AREA (NO FULL REFRESH)
# =========================
st.subheader("💰 Live Prices")

price_boxes = {}
cols = st.columns(len(coins))

for i, c in enumerate(coins):
    price_boxes[c] = cols[i].empty()

# =========================
# SIGNAL AREA
# =========================
st.subheader(f"📈 AI Signals: {symbol}")

signal_box = st.empty()

# =========================
# MAIN LOOP (LIGHTWEIGHT)
# =========================
while True:

    # -------- LIVE PRICES --------
    for c in coins:
        price = get_price(c)

        if price:
            price_boxes[c].metric(c, f"${price:,.2f}")
        else:
            price_boxes[c].metric(c, "—")

    # -------- AI ANALYSIS --------
    signals = {}

    for tf_name, tf_value in timeframes.items():

        df = get_data(symbol, tf_value)

        if df is None:
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

    buy_count = list(signals.values()).count("🟢 BUY")
    sell_count = list(signals.values()).count("🔴 SELL")

    if signals.get("1D") == "🟢 BUY" and buy_count >= 2:
        final = "🟢 STRONG BUY"
    elif signals.get("1D") == "🔴 SELL" and sell_count >= 2:
        final = "🔴 STRONG SELL"
    else:
        final = "⚪ NO CLEAR SIGNAL"

    signal_box.markdown(f"## {final}")

    # -------- SLEEP --------
    time.sleep(2)
