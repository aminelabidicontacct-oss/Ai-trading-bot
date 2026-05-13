import streamlit as st
import ccxt
import pandas as pd
import ta
import joblib
import time

# ==========================================
# 1. الإعدادات العامة (Configuration)
# ==========================================
st.set_page_config(layout="wide", page_title="AI Trading Pro - Kucoin")
st.title("📊 AI Trading Dashboard (Kucoin Edition)")

# تحميل النموذج (AI Model)
@st.cache_resource
def load_model():
    try:
        return joblib.load("ai_trading_model.pkl")
    except:
        st.error("⚠️ ملف النموذج 'ai_trading_model.pkl' غير موجود في المسار!")
        return None

model = load_model()

# الاتصال بمنصة Kucoin
exchange = ccxt.kucoin({
    'enableRateLimit': True,
})

# القائمة والعملات (نفس التي تتابعها)
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TIMEFRAMES = {"1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}

# ==========================================
# 2. جلب وتحليل البيانات (Data Logic)
# ==========================================
def fetch_and_analyze(symbol, timeframe):
    """جلب البيانات من Kucoin وحساب المؤشرات"""
    try:
        # جلب الشموع (OHLCV)
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات الفنية
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(10).std()
        
        return df.dropna().iloc[-1] # إرجاع آخر شمعة مكتملة
    except Exception as e:
        return None

# ==========================================
# 3. واجهة المستخدم (UI Layout)
# ==========================================
selected_symbol = st.sidebar.selectbox("📌 اختر العملة للتحليل", COINS)
st.sidebar.info("يتم تحديث البيانات من منصة Kucoin تلقائياً.")

# عرض الأسعار المباشرة في الأعلى
st.subheader("💰 الأسعار الحالية (Live)")
price_cols = st.columns(len(COINS))
price_placeholders = [col.empty() for col in price_cols]

# منطقة عرض إشارة الذكاء الاصطناعي
st.divider()
st.subheader(f"📈 إشارات الذكاء الاصطناعي: {selected_symbol}")
signal_placeholder = st.empty()

# ==========================================
# 4. الحلقة الرئيسية (Execution Loop)
# ==========================================
while True:
    # أ. تحديث الأسعار لكل العملات
    for i, coin in enumerate(COINS):
        try:
            ticker = exchange.fetch_ticker(f"{coin}/USDT")
            price = ticker['last']
            price_placeholders[i].metric(coin, f"${price:,.4f}")
        except:
            price_placeholders[i].metric(coin, "N/A")

    # ب. تحليل العملة المختارة بالذكاء الاصطناعي
    if model:
        last_data = fetch_and_analyze(selected_symbol, "1h")
        
        if last_data is not None:
            # تجهيز الميزات للنموذج
            features = [[
                last_data['rsi'], 
                last_data['ema50'], 
                last_data['ema200'], 
                last_data['return'], 
                last_data['volatility']
            ]]
            
            # التنبؤ
            proba = model.predict_proba(features)[0]
            buy_score = proba[1]
            
            if buy_score > 0.7:
                status, color = "🟢 شراء قوي (Strong Buy)", "green"
            elif buy_score < 0.3:
                status, color = "🔴 بيع (Sell)", "red"
            else:
                status, color = "⚪ انتظار (Neutral)", "gray"
            
            signal_placeholder.markdown(
                f"<div style='padding:20px; border-radius:10px; background-color:#1e1e1e; border: 2px solid {color};'>"
                f"<h2 style='color:{color}; text-align:center;'>{status}</h2>"
                f"<p style='text-align:center;'>إحتمالية الصعود: {buy_score:.2%}</p>"
                f"</div>", 
                unsafe_allow_html=True
            )
    
    # انتظار قبل التحديث القادم لتجنب الحظر من Kucoin
    time.sleep(10)
    
