import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import time
import requests

# ==========================================
# 1. CONFIGURATION & LANGUAGES
# ==========================================
st.set_page_config(layout="wide", page_title="AI Swing Trader - Kucoin")

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
        "title": "📊 لوحة التداول بالذكاء الاصطناعي",
        "coin": "📌 اختر العملة",
        "tf": "⏱️ اختر الفريم",
        "price": "💰 الأسعار المباشرة",
        "entry": "🎯 منطقة الدخول",
        "target": "🚀 الهدف",
        "signal": "📈 إشارة الذكاء الاصطناعي",
        "lang": "🌐 اللغة"
    }
}

st.sidebar.header("🛠️ Settings")

selected_lang = st.sidebar.selectbox("Language", list(translations.keys()))
t = translations[selected_lang]

# ==========================================
# 2. MODEL
# ==========================================
@st.cache_resource
def load_model():
    return joblib.load("ai_trading_model.pkl")

model = load_model()

# ==========================================
# 3. EXCHANGES (FALLBACK SYSTEM)
# ==========================================
kucoin = ccxt.kucoin({'enableRateLimit': True})
coinbase = ccxt.coinbase({'enableRateLimit': True})
okx = ccxt.okx({'enableRateLimit': True})

def get_price(symbol):
    # Binance REST
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        r = requests.get(url, timeout=2).json()
        return float(r["price"])
    except:
        pass

    # KuCoin
    try:
        return float(kucoin.fetch_ticker(f"{symbol}/USDT")["last"])
    except:
        pass

    # OKX
    try:
        return float(okx.fetch_ticker(f"{symbol}/USDT")["last"])
    except:
        pass

    # Coinbase
    try:
        return float(coinbase.fetch_ticker(f"{symbol}/USDT")["last"])
    except:
        pass

    return None

# ==========================================
# 4. MARKET DATA
# ==========================================
exchange = kucoin

COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TF_MAP = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}

coin = st
