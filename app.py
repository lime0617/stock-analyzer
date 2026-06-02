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
st.markdown("**近30日量价分析 | 大白话解读 + 买卖建议**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ 或 .SS")
    analyze_button = st.button("🚀 开始分析", type="primary")

@st.cache_data(ttl=300)
def get_stock_data(symbol):
    df = yf.Ticker(symbol).history(period="60d")
    return df.tail(30)

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol} 近30日表现..."):
        try:
            df = get_stock_data(symbol)
            
            if len(df) < 20:
                st.error("数据不足，请稍后重试")
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
            prev = df.iloc[-2] if len(df) > 1 else latest

            # ==================== 综合评分 ====================
            score = 5.0
            reasons = []
            
            if latest['Close'] > latest['MA5'] and latest['MA5'] > latest['MA10']:
                score += 2.0
                reasons.append("✅ 短期均线向上，趋势较好")
            if latest['RSI'] < 40:
                score += 2.0
                reasons.append("🟢 RSI处于低位，超卖区")
            elif latest['RSI'] > 70:
                score -= 2.0
                reasons.append("🔴 RSI过高，超买区")
            if latest['Volume_Ratio'] > 1.5:
                score += 1.5
                reasons.append("🔥 出现放量，关注度提升")
            if latest['Close'] > df['Close'].mean():
                score += 0.5

            final_score = min(10, max(1, round(score, 1)))

            # ==================== 显示内容 ====================
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("近30日涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("综合评分", f"{final_score} / 10 分")

            # 图表
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
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

            # 大白话总结 + 买卖建议
            st.subheader("📋 大白话分析总结")
            st.write(f"**综合评分**：**{final_score} 分 / 10 分**")
            
            for reason in reasons:
                st.write(reason)
            
            st.subheader("💡 买卖建议")
            if final_score >= 8.5:
                st.success("🔥 **强烈建议买入**（多指标共振，机会较好）")
            elif final_score >= 7:
                st.success("🟢 **可以考虑买入**（趋势向好）")
            elif final_score >= 5.5:
                st.info("🟡 **观望为主**，出现回调时可分批买入")
            else:
                st.warning("⚠️ **暂不建议买入**，等待更好时机")

            st.caption("⚠️ 以上仅为技术分析参考，请结合自身风险承受能力决策")

        except Exception as e:
            st.error("分析失败，请等待1分钟后再试")

st.caption("由 Grok 构建 | 仅供学习参考")import streamlit as st
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
st.markdown("**近30日量价分析 | 大白话解读 + 买卖建议**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ 或 .SS")
    analyze_button = st.button("🚀 开始分析", type="primary")

@st.cache_data(ttl=300)
def get_stock_data(symbol):
    df = yf.Ticker(symbol).history(period="60d")
    return df.tail(30)

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol} 近30日表现..."):
        try:
            df = get_stock_data(symbol)
            
            if len(df) < 20:
                st.error("数据不足，请稍后重试")
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
            prev = df.iloc[-2] if len(df) > 1 else latest

            # ==================== 综合评分 ====================
            score = 5.0
            reasons = []
            
            if latest['Close'] > latest['MA5'] and latest['MA5'] > latest['MA10']:
                score += 2.0
                reasons.append("✅ 短期均线向上，趋势较好")
            if latest['RSI'] < 40:
                score += 2.0
                reasons.append("🟢 RSI处于低位，超卖区")
            elif latest['RSI'] > 70:
                score -= 2.0
                reasons.append("🔴 RSI过高，超买区")
            if latest['Volume_Ratio'] > 1.5:
                score += 1.5
                reasons.append("🔥 出现放量，关注度提升")
            if latest['Close'] > df['Close'].mean():
                score += 0.5

            final_score = min(10, max(1, round(score, 1)))

            # ==================== 显示内容 ====================
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("近30日涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("综合评分", f"{final_score} / 10 分")

            # 图表
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
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

            # 大白话总结 + 买卖建议
            st.subheader("📋 大白话分析总结")
            st.write(f"**综合评分**：**{final_score} 分 / 10 分**")
            
            for reason in reasons:
                st.write(reason)
            
            st.subheader("💡 买卖建议")
            if final_score >= 8.5:
                st.success("🔥 **强烈建议买入**（多指标共振，机会较好）")
            elif final_score >= 7:
                st.success("🟢 **可以考虑买入**（趋势向好）")
            elif final_score >= 5.5:
                st.info("🟡 **观望为主**，出现回调时可分批买入")
            else:
                st.warning("⚠️ **暂不建议买入**，等待更好时机")

            st.caption("⚠️ 以上仅为技术分析参考，请结合自身风险承受能力决策")

        except Exception as e:
            st.error("分析失败，请等待1分钟后再试")

st.caption("由 小胖虎 构建 | 仅供学习参考")
