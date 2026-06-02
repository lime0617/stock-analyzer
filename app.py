import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta
import warnings
import numpy as np

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**支持输入股票名称或代码 | 大白话解读**")

with st.sidebar:
    st.header("分析设置")
    user_input = st.text_input("股票名称或代码", value="中航西飞", help="可以直接输入名称，如：中航西飞、贵州茅台、苹果")
    analyze_button = st.button("🚀 开始分析", type="primary")

@st.cache_data(ttl=3600)
def get_symbol_from_name(name):
    """名称转代码"""
    try:
        # A股搜索
        stock_list = ak.stock_info_a_code_name()
        match = stock_list[stock_list['name'].str.contains(name, na=False)]
        if not match.empty:
            code = match.iloc[0]['code']
            return f"{code}.SZ" if code.startswith('0') or code.startswith('3') else f"{code}.SS"
    except:
        pass
    return name  # 如果没找到，直接返回原输入（可能是代码）

if analyze_button and user_input:
    with st.spinner(f"正在查找并分析 {user_input}..."):
        try:
            # 处理输入（名称或代码）
            symbol = get_symbol_from_name(user_input)
            
            df = yf.Ticker(symbol).history(period="60d")
            df = df.tail(30).copy()
            
            if len(df) < 20:
                st.error("未找到该股票或数据不足，请尝试更准确的名称")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            df['Volume_Ratio'] = df['Volume'] / vol_mean
            
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

            # 图表展示（省略部分代码以保持简洁，保持之前样式）
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            
            fig.update_layout(height=750, title_text=f"{user_input} ({symbol}) 近30日分析")
            st.plotly_chart(fig, use_container_width=True)

            # 总结
            st.subheader("📋 大白话总结")
            st.metric("综合评分", f"{final_score} / 10 分")
            
            if final_score >= 8:
                st.success("🔥 近期表现较强，值得重点关注")
            elif final_score >= 6:
                st.info("🟡 表现中等，可继续观察")
            else:
                st.warning("⚪ 目前表现一般，建议谨慎")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:80]}... 请尝试更准确的股票名称")

st.caption("由 Grok 构建 | 支持名称搜索 | 仅供参考")
