import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票全景智能分析器")
st.markdown("**近30日量价 + 基本面 + 机构行为 + 大白话解读**")

with st.sidebar:
    st.header("分析设置")
    user_input = st.text_input("股票名称或代码", value="000768", help="支持名称或代码")
    analyze_button = st.button("🚀 开始全景分析", type="primary")

if analyze_button and user_input:
    with st.spinner(f"正在进行 {user_input} 全景分析..."):
        try:
            # 获取基本数据
            symbol = user_input
            if not any(x in symbol for x in ['.SZ','.SH','.SS']):
                # 简单名称转代码
                try:
                    code_df = ak.stock_info_a_code_name()
                    match = code_df[code_df['name'].str.contains(user_input)]
                    if not match.empty:
                        code = match.iloc[0]['code']
                        symbol = f"{code}.SZ" if code.startswith(('0','3')) else f"{code}.SS"
                except:
                    pass

            df = yf.Ticker(symbol).history(period="90d")
            df = df.tail(30).copy()

            # ==================== 基础量价分析 ====================
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
            if latest['Close'] > latest['MA5']: score += 1.5
            if latest['RSI'] < 40: score += 2.0
            if latest['Volume_Ratio'] > 1.5: score += 1.5
            final_score = min(10, max(1, round(score, 1)))

            # ==================== 展示 ====================
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("近30日涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("综合技术评分", f"{final_score} / 10 分")

            # 主图表
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.45, 0.3, 0.25])
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI'), row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 大白话总结与建议")
            if final_score >= 8:
                st.success("🔥 **值得重点关注**，短期趋势较好")
            elif final_score >= 6:
                st.info("🟡 **表现中等**，可继续观察")
            else:
                st.warning("⚪ **目前一般**，建议谨慎")

            st.write("**买卖建议**：")
            if final_score >= 8:
                st.success("✅ **建议分批买入**")
            elif final_score >= 6.5:
                st.info("🟡 **回调时可考虑买入**")
            else:
                st.warning("⚠️ **暂不建议重仓**")

            st.caption("功能正在持续扩展中... 后续会加入板块、十大股东、机构持仓等信息")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")

st.caption("由 Grok 构建 | 持续优化中")
