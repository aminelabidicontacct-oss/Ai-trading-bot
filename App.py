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

# تحميل نموذج الذكاء الاصطناعي
@st.cache_resource
def load_model():
    try:
        return joblib.load("ai_trading_model.pkl")
    except Exception as e:
        st.error(f"⚠️ خطأ في تحميل النموذج: {e}")
        return None

model = load_model()

# الاتصال بمنصة Kucoin عبر مكتبة CCXT
exchange = ccxt.kucoin({'enableRateLimit': True})

# العملات والفريمات المفضلة لأمين
COINS = ["BTC", "ETH", "SOL", "SUI", "ANKR", "BNB"]
TIMEFRAMES = {"1 Day (Long Term)": "1d", "4 Hours": "4h", "1 Hour": "1h", "15 Minutes": "15m"}

# ==========================================
# 2. منطق جلب البيانات وتحليلها
# ==========================================
def fetch_and_analyze(symbol, timeframe):
    try:
        # جلب بيانات الشموع
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات الفنية التي يتابعها أمين
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(10).std()
        
        return df.dropna().iloc[-1], df # إرجاع آخر شمعة والبيانات كاملة
    except Exception as e:
        return None, None

# ==========================================
# 3. واجهة المستخدم الجانبية (Sidebar)
# ==========================================
st.sidebar.header("🛠️ إعدادات البوت")
selected_symbol = st.sidebar.selectbox("📌 اختر العملة", COINS)
selected_tf_name = st.sidebar.selectbox("⏱️ اختر الفريم الزمني", list(TIMEFRAMES.keys()), index=2)
selected_tf_val = TIMEFRAMES[selected_tf_name]

st.sidebar.divider()
st.sidebar.info("هذا البوت يحلل البيانات بناءً على استراتيجيتك الاستثمارية لعام 2029.")

# ==========================================
# 4. الحلقة الرئيسية (Execution Loop)
# ==========================================
# عرض الأسعار المباشرة في الأعلى
st.subheader("💰 أسعار السوق الحالية")
price_cols = st.columns(len(COINS))
price_placeholders = [col.empty() for col in price_cols]

st.divider()
signal_placeholder = st.empty()
entry_placeholder = st.sidebar.empty()

while True:
    # أ. تحديث الأسعار الحية لكل العملات
    for i, coin in enumerate(COINS):
        try:
            ticker = exchange.fetch_ticker(f"{coin}/USDT")
            price_placeholders[i].metric(coin, f"${ticker['last']:.4f}")
        except:
            price_placeholders[i].metric(coin, "N/A")

    # ب. تحليل العملة المختارة بالذكاء الاصطناعي وتحديد الأهداف
    last_data, full_df = fetch_and_analyze(selected_symbol, selected_tf_val)
    
    if model and last_data is not None:
        # تجهيز البيانات للنموذج
        features = [[
            last_data['rsi'], last_data['ema50'], last_data['ema200'], 
            last_data['return'], last_data['volatility']
        ]]
        
        proba = model.predict_proba(features)[0]
        buy_score = proba[1]
        current_price = last_data['close']

        # منطق تحديد نقطة الدخول (Entry Point)
        # إذا كان الاحتمال عالٍ والسعر قريب من الدعم أو الـ RSI منخفض
        entry_price = last_data['ema50'] if current_price > last_data['ema50'] else current_price * 0.99
        
        # عرض الإشارة
        if buy_score > 0.7:
            status, color = "🟢 إشارة شراء قوية (Strong Buy)", "#00ff00"
        elif buy_score < 0.3:
            status, color = "🔴 إشارة بيع/خروج (Sell)", "#ff0000"
        else:
            status, color = "⚪ حالة انتظار (Neutral)", "#808080"

        signal_placeholder.markdown(
            f"<div style='padding:20px; border-radius:10px; border: 2px solid {color}; text-align:center;'>"
            f"<h2 style='color:{color};'>{status}</h2>"
            f"<h3>إحتمالية الصعود: {buy_score:.2%}</h3>"
            f"</div>", unsafe_allow_html=True
        )

        # عرض نقطة الدخول والهدف في القائمة الجانبية
        entry_placeholder.markdown(
            f"--- \n"
            f"🎯 **نقطة الدخول المثالية:** `${entry_price:.4f}` \n\n"
            f"🚀 **هدف استثمار 2029:** `${entry_price * 5:.2f}`"
        )

    time.sleep(15) # انتظار لتجنب الحظر من API المنصة
