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
st.markdown("**专注近30日量价分析 | 大白话解读**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ/.SS\n美股直接输入")
    analyze_button = st.button("🚀 开始分析", type="primary")

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol} 近30日表现..."):
        try:
            df = yf.Ticker(symbol).history(period="60d")
            df = df.tail(30).copy()   # 固定近30个交易日
            
            if len(df) < 20:
                st.error("数据不足，请尝试其他股票")
                st.stop()

            # ==================== 计算指标 ====================
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            # 量能分析
            vol_mean = df['Volume'].mean()
            vol_ma5 = df['Volume'].rolling(5).mean()
            df['Volume_Change'] = df['Volume'] / vol_mean
            
            # 温和放量判断
            mild_volume = (df['Volume_Change'] > 1.2) & (df['Volume_Change'] < 2.0)
            has_mild_volume = mild_volume.any()
            
            # 量能异常
            strong_volume = df['Volume_Change'] > 2.0
            weak_volume = df['Volume_Change'] < 0.5
            
            # RSI（超买超卖）
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            latest = df.iloc[-1]
            
            # ==================== 评分系统 ====================
            score = 5.0  # 基准分
            
            if latest['Close'] > latest['MA5'] and latest['MA5'] > latest['MA10']:
                score += 2.0
            if latest['RSI'] < 35:
                score += 2.0
            elif latest['RSI'] > 75:
                score -= 2.0
                
            if latest['Volume_Change'] > 1.5:
                score += 1.5
                
            final_score = min(10, max(1, round(score, 1)))

            # ==================== 显示结果 ====================
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("30日涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("综合评分", f"{final_score} / 10 分")
            
            # 主图表
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
            
            fig.update_layout(height=800, title_text=f"{symbol} 近30日量价分析")
            st.plotly_chart(fig, use_container_width=True)

            # 筹码分布图
            st.subheader("🧿 筹码分布图（近似）")
            prices = df['Close']
            volumes = df['Volume']
            bins = np.linspace(prices.min()*0.95, prices.max()*1.05, 40)
            digitized = np.digitize(prices, bins)
            chip = np.zeros(len(bins))
            for i in range(len(prices)):
                chip[digitized[i]-1] += volumes.iloc[i]
            
            fig_chip = go.Figure()
            fig_chip.add_trace(go.Bar(x=bins, y=chip, marker_color='coral'))
            fig_chip.update_layout(title="筹码分布（成交量在各价格区间的集中情况）", 
                                 xaxis_title="股价区间", yaxis_title="成交量权重", height=400)
            st.plotly_chart(fig_chip, use_container_width=True)

            # 大白话分析
            st.subheader("📋 分析总结（大白话）")
            st.write(f"**综合评分**：{final_score} 分（满分10分）")
            
            if final_score >= 8:
                st.success("🔥 整体表现较强，值得重点关注")
            elif final_score >= 6:
                st.info("🟡 表现中等，可继续观察")
            else:
                st.warning("⚪ 目前表现一般，建议谨慎")

            st.write("**量能情况**：", "有温和放量" if has_mild_volume.any() else "放量不明显")
            st.write("**量能异常**：", "出现明显放量" if strong_volume.any() else "量能正常")
            st.write("**超买超卖**：", "处于超卖区" if latest['RSI'] < 35 else "处于超买区" if latest['RSI'] > 70 else "处于正常区间")

            st.subheader("💡 开仓/买卖建议")
            if final_score >= 8:
                st.success("✅ **建议考虑开仓**（可分批买入）")
            elif final_score >= 6.5:
                st.info("🟡 **可以观察，出现回调时可尝试买入**")
            else:
                st.warning("⚠️ **暂不建议开仓**，等待更好机会")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:120]}")

st.caption("由 Grok 构建 | 仅供学习参考 · 非投资建议")
