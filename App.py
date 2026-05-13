import streamlit as st
import joblib
import requests
import pandas as pd
import ta

st.title("⚡ AI Trading Bot")

model = joblib.load("ai_trading_model.pkl")

def get_data():
    url = "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=200"
    data = requests.get(url).json()

    if "Data" not in data:
        return None

    df = pd.DataFrame(data["Data"]["Data"])

    if df.empty:
        return None

    df["rsi"] = ta.momentum.rsi(df["close"], 14)
    df["ema50"] = ta.trend.ema_indicator(df["close"], 50)
    df["ema200"] = ta.trend.ema_indicator(df["close"], 200)

    df["return"] = df["close"].pct_change()
    df["volatility"] = df["close"].rolling(10).std()

    df = df.dropna()

    return df

df = get_data()

if df is None or len(df) == 0:
    st.warning("Waiting for data...")
    st.stop()

last = df.iloc[-1]

features = [[
    last["rsi"],
    last["ema50"],
    last["ema200"],
    last["return"],
    last["volatility"]
]]

proba = model.predict_proba(features)[0]

buy = proba[1]
sell = proba[0]

st.subheader("Signal")

if buy > 0.7:
    st.success(f"🟢 STRONG BUY ({buy:.2f})")
elif sell > 0.7:
    st.error(f"🔴 STRONG SELL ({sell:.2f})")
else:
    st.warning(f"⚪ WAIT ({buy:.2f}/{sell:.2f})")

st.dataframe(df.tail())
