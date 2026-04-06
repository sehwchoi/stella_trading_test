import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os


# ------------------------
# 비밀번호 보호
# ------------------------
password = st.text_input("🔒 비밀번호 입력", type="password")

if password != os.getenv("APP_PASSWORD"):
    st.stop()

# ------------------------
# VWAP 계산
# ------------------------
def calculate_vwap(df):
    df['cum_vol_price'] = (df['Close'] * df['Volume']).cumsum()
    df['cum_vol'] = df['Volume'].cumsum()
    df['VWAP'] = df['cum_vol_price'] / df['cum_vol']
    return df

# ------------------------
# 매수 신호 함수
# ------------------------
def generate_buy_signal(df):
    try:
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df = calculate_vwap(df)

        if len(df) < 20:
            return "HOLD", None, df, None, None, None, None, None

        latest = df.iloc[-1].copy()
        prev = df.iloc[-2].copy()

        avg_volume = float(df['Volume'].mean())
        recent_high = float(df['High'].rolling(20).max().iloc[-2])

        # 숫자 변환
        latest_close = float(latest['Close'])
        latest_vwap = float(latest['VWAP'])
        latest_ma5 = float(latest['MA5'])
        latest_ma20 = float(latest['MA20'])
        latest_volume = float(latest['Volume'])

        prev_close = float(prev['Close'])
        prev_ma20 = float(prev['MA20'])
        prev_vwap = float(prev['VWAP'])

        # 조건
        trend_ok = latest_close > latest_vwap
        ma_ok = latest_ma5 > latest_ma20
        volume_ok = latest_volume > avg_volume * 1.5
        breakout = latest_close > recent_high

        pullback = (
            (prev_close < prev_ma20 or prev_close < prev_vwap)
            and (latest_close > prev_close)
        )

        if trend_ok and ma_ok and volume_ok and (breakout or pullback):
            return "BUY", latest, df, trend_ok, ma_ok, volume_ok, breakout, pullback

        return "HOLD", latest, df, trend_ok, ma_ok, volume_ok, breakout, pullback

    except Exception as e:
        print("ERROR:", e)
        return "HOLD", None, df, None, None, None, None, None

# ------------------------
# UI 시작
# ------------------------
st.title("📈 AI Trading Dashboard")

# 섹터 선택
sector = st.selectbox(
    "섹터 선택",
    ["AI", "Robotics", "Manufacturing"]
)

# 섹터별 종목
sector_stocks = {
    "AI": ["NVDA", "AMD", "MSFT", "GOOGL", "META", "TSM", "AVGO", "PLTR", "SNOW", "AI"],
    "Robotics": ["ISRG", "ABB", "FANUY", "ROK", "TER", "PATH", "SYM", "IRBT", "ZBRA", "CGNX"],
    "Manufacturing": ["CAT", "DE", "HON", "GE", "BA", "MMM", "ETN", "EMR", "ITW", "PH"]
}

stocks = sector_stocks[sector]

# 종목 선택
selected_stock = st.selectbox("종목 선택", stocks)

# ------------------------
# 데이터 가져오기
# ------------------------
df = yf.download(selected_stock, interval="5m", period="1d")

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# ------------------------
# 차트 + 신호
# ------------------------
if df.empty:
    st.error("데이터 없음")
else:
    signal, latest, df, trend_ok, ma_ok, volume_ok, breakout, pullback = generate_buy_signal(df)

    st.subheader(f"{selected_stock} Chart")

    df_plot = df.tail(50).copy().dropna()

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], name='Close'))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA5'], name='MA5'))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MA20'], name='MA20'))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['VWAP'], name='VWAP'))

    y_min = df_plot['Close'].min() * 0.995
    y_max = df_plot['Close'].max() * 1.005

    fig.update_layout(height=500, yaxis=dict(range=[y_min, y_max]))

    st.plotly_chart(fig, use_container_width=True)

    if latest is not None:
        st.write("현재 가격:", latest['Close'])
        st.write("VWAP:", latest['VWAP'])

    if signal == "BUY":
        st.success("🚀 BUY SIGNAL")
    else:
        st.warning("⏳ NO SIGNAL")

    st.subheader("📊 조건 분석")
    st.write("VWAP 위:", trend_ok)
    st.write("MA 상승:", ma_ok)
    st.write("거래량 증가:", volume_ok)
    st.write("돌파 여부:", breakout)
    st.write("눌림 반등:", pullback)

# ------------------------
# 🔍 섹터 전체 스캔
# ------------------------
st.divider()
st.subheader("🔍 섹터 전체 스캔")

if st.button("🚀 BUY 종목 찾기"):
    results = []

    for s in stocks:
        try:
            df_scan = yf.download(s, interval="5m", period="1d")

            if isinstance(df_scan.columns, pd.MultiIndex):
                df_scan.columns = df_scan.columns.get_level_values(0)

            if df_scan.empty or len(df_scan) < 20:
                continue

            signal, _, _, *_ = generate_buy_signal(df_scan)

            if signal == "BUY":
                results.append(s)

        except:
            continue

    if results:
        st.success("🚀 BUY 종목")
        st.table(pd.DataFrame(results, columns=["Ticker"]))
    else:
        st.warning("❌ 현재 BUY 없음")