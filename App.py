import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📊 AI Trading Dashboard")

# =========================
# MODEL
# =========================
model = joblib.load("ai_trading_model.pkl")

# =========================
# EXCHANGE
# =========================
exchange = ccxt.kucoin({'enableRateLimit': True})

# =========================
# COINS + TF
# =========================
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}

coin = st.selectbox("Coin", COINS)
tf = st.selectbox("Timeframe", list(TF_MAP.keys()))
timeframe = TF_MAP[tf]

# =========================
# PRICE (SAFE)
# =========================
def get_price(symbol):
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT",
            timeout=3
        ).json()
        return float(r["price"])
    except:
        try:
            return float(exchange.fetch_ticker(f"{symbol}/USDT")["last"])
        except:
            return None

# =========================
# DATA
# =========================
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

cols = st.columns(len(COINS))

for i, c in enumerate(COINS):
    price = get_price(c)
    cols[i].metric(c, f"${price:.2f}" if price else "—")

# =========================
# AI SIGNAL
# =========================
df = get_data(coin, timeframe)

if df is not None:

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

    st.markdown(f"""
    ## {signal}
    💰 Price: `{last['close']:.2f}`
    """)

else:
    st.warning("No data available")
