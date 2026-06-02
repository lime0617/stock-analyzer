import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import numpy as np
import time

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**近30日量价分析 | 大白话解读**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ/.SS")
    analyze_button = st.button("🚀 开始分析", type="primary")

@st.cache_data(ttl=300)  # 缓存5分钟
def get_stock_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="60d")
        return df.tail(30)
    except:
        time.sleep(2)
        return yf.Ticker(symbol).history(period="60d").tail(30)

if analyze_button and symbol:
    with st.spinner(f"正在获取 {symbol} 数据..."):
        try:
            df = get_stock_data(symbol)
            
            if len(df) < 20:
                st.error("数据获取失败，请稍等1分钟后再试")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            df['Volume_Ratio'] = df['Volume'] / vol_mean
            
            # RSI
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            latest = df.iloc[-1]
            
            # 评分
            score = 5.0
            if latest['Close'] > latest['MA5']:
                score += 1.5
            if latest['RSI'] < 40:
                score += 2.0
            if latest['Volume_Ratio'] > 1.5:
                score += 1.5
            final_score = min(10, max(1, round(score, 1)))

            # 主图表
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='lightblue'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
            
            fig.update_layout(height=750, title_text=f"{symbol} 近30日量价分析")
            st.plotly_chart(fig, use_container_width=True)

            # 筹码分布
            st.subheader("🧿 筹码分布图（近似）")
            prices = df['Close']
            volumes = df['Volume']
            bins = np.linspace(prices.min()*0.95, prices.max()*1.05, 40)
            digitized = np.digitize(prices, bins)
            chip = np.zeros(len(bins))
            for i in range(len(prices)):
                chip[digitized[i]-1] += volumes.iloc[i]
            
            fig_chip = go.Figure(go.Bar(x=bins, y=chip, marker_color='coral'))
            fig_chip.update_layout(title="筹码分布（成交量在不同价格区间的集中度）", 
                                 xaxis_title="股价区间", yaxis_title="成交量权重", height=400)
            st.plotly_chart(fig_chip, use_container_width=True)

            # 总结
            st.subheader("📋 大白话总结")
            st.metric("综合评分", f"{final_score} / 10 分")
            
            if final_score >= 8:
                st.success("🔥 表现较强，值得关注")
            elif final_score >= 6:
                st.info("🟡 表现中等，可继续观察")
            else:
                st.warning("⚪ 目前表现一般，建议谨慎")

        except Exception as e:
            st.error("请求太频繁，请等待1-2分钟后再试")
            st.info("yfinance 有请求限制，建议不要频繁点击分析")

st.caption("由 Grok 构建 | 仅供参考")
