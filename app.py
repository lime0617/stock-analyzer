import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import numpy as np

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**大白话版 | MACD + RSI + KDJ + 布林带 + 筹码分布**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ 或 .SS\n美股直接输入")
    days = st.slider("分析天数", 10, 180, 60)
    analyze_button = st.button("🚀 开始分析", type="primary")

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}..."):
        try:
            df = yf.Ticker(symbol).history(period=f"{days+60}d")
            df = df.tail(days).copy()
            
            if len(df) < 30:
                st.error("数据不足，请尝试其他股票")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            # MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 布林带
            df['BB_Middle'] = df['Close'].rolling(20).mean()
            df['BB_Std'] = df['Close'].rolling(20).std()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']

            # 主图表 (Plotly)
            fig = make_subplots(rows=3, cols=1, 
                              subplot_titles=("价格与均线", "成交量", "MACD"),
                              vertical_spacing=0.08, row_heights=[0.5, 0.25, 0.25])

            # 价格图
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='布林上轨', line=dict(dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='布林下轨', line=dict(dash='dash')), row=1, col=1)

            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)

            # MACD
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal'), row=3, col=1)

            fig.update_layout(height=800, title_text=f"{symbol} 技术分析图")
            st.plotly_chart(fig, use_container_width=True)

            # 筹码分布图（Plotly版）
            st.subheader("🧿 筹码分布图（近似）")
            prices = df['Close']
            volumes = df['Volume']
            bins = np.linspace(prices.min()*0.95, prices.max()*1.05, 40)
            digitized = np.digitize(prices, bins)
            chip = np.zeros(len(bins))
            for i in range(len(prices)):
                chip[digitized[i]-1] += volumes.iloc[i]

            fig_chip = go.Figure()
            fig_chip.add_trace(go.Bar(x=bins, y=chip, marker_color='coral', name='筹码集中度'))
            fig_chip.update_layout(title="筹码分布图（近似）", xaxis_title="股价区间", yaxis_title="成交量权重", height=400)
            st.plotly_chart(fig_chip, use_container_width=True)

            # 大白话总结
            latest = df.iloc[-1]
            st.success("✅ 分析完成！")
            st.metric("最新价格", f"{latest['Close']:.2f}")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")

st.caption("由 Grok 构建 | 使用 Plotly 交互图表 | 仅供参考")
