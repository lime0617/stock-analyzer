import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import numpy as np

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**大白话版 | 附风险评估 + 止损建议**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="美股直接输代码，A股建议加 .SZ 或 .SS")
    days = st.slider("分析天数", 10, 180, 60)
    analyze_button = st.button("🚀 开始分析", type="primary")

def generate_easy_explanation_and_score(df):
    latest = df.iloc[-1]
    score = 0
    reasons = []
    risk_level = "中等"
    stop_loss = "暂无"

    # MACD（趋势）
    if latest['MACD'] > latest['Signal']:
        score += 2.5
        reasons.append("✅ 短期趋势向上（MACD金叉）")
    else:
        reasons.append("🔸 短期趋势偏弱")

    # RSI（超买超卖）
    if latest['RSI'] < 35:
        score += 2
        reasons.append("🟢 当前价格处于低位（容易反弹）")
    elif latest['RSI'] > 70:
        score -= 2
        reasons.append("🔴 当前价格偏高（有回调风险）")
    else:
        reasons.append("⚪ 当前价格处于合理区间")

    # KDJ
    if latest['K'] < 30:
        score += 1.5
        reasons.append("🟢 短期超卖，容易出现反弹")

    # 布林带
    if latest['Close'] < latest['BB_Lower']:
        score += 2
        reasons.append("🟢 价格已经跌到较低位置")
    elif latest['Close'] > latest['BB_Upper']:
        score -= 2
        reasons.append("🔴 价格已经涨到较高位置")

    # 综合评分（1-10分）
    final_score = min(10, max(1, round(score + 5)))   # 基准5分

    # 风险评估和止损建议
    volatility = df['Close'].pct_change().std() * 100
    if final_score >= 8:
        risk_level = "较低"
        stop_loss = f"建议止损位：{latest['Close'] * 0.92:.2f}（跌破约8%止损）"
    elif final_score >= 6:
        risk_level = "中等"
        stop_loss = f"建议止损位：{latest['Close'] * 0.90:.2f}（跌破约10%止损）"
    else:
        risk_level = "较高"
        stop_loss = f"建议止损位：{latest['Close'] * 0.88:.2f}（跌破约12%止损）"

    return final_score, reasons, risk_level, stop_loss

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
            
            # RSI & KDJ & 布林带
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            low_min = df['Low'].rolling(9).min()
            high_max = df['High'].rolling(9).max()
            rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
            df['K'] = rsv.ewm(com=2, adjust=False).mean()
            df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            df['J'] = 3 * df['K'] - 2 * df['D']
            
            df['BB_Middle'] = df['Close'].rolling(20).mean()
            df['BB_Std'] = df['Close'].rolling(20).std()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']

            # 生成大白话建议
            score, reasons, risk_level, stop_loss = generate_easy_explanation_and_score(df)
            
            # 显示图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            ax1.plot(df.index, df['Close'], label='收盘价', linewidth=2)
            ax1.plot(df.index, df['MA5'], label='5日均线')
            ax1.plot(df.index, df['MA10'], label='10日均线')
            ax1.plot(df.index, df['MA20'], label='20日均线')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            ax2.bar(df.index, df['Volume'], color='skyblue', alpha=0.7)
            ax2.set_ylabel('成交量')
            plt.tight_layout()
            st.pyplot(fig)
            
            # 结果展示
            col1, col2 = st.columns(2)
            latest = df.iloc[-1]
            
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("期间涨跌幅", f"{change:+.2f}%")
            
            with col2:
                st.metric("RSI", f"{latest['RSI']:.1f}")
            
            st.subheader("📊 综合评分")
            st.markdown(f"**{score} 分 / 10 分**（{score}分：{'非常值得关注' if score >= 8 else '值得观察' if score >= 6 else '暂不推荐'}）")
            
            st.subheader("💡 大白话分析")
            for reason in reasons:
                st.write(reason)
            
            st.subheader("⚠️ 风险评估 & 止损建议")
            st.write(f"**风险等级**：{risk_level}")
            st.write(f"**建议止损位**：{stop_loss}")
            
        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")

st.caption("由 Grok 构建 | 以上内容仅供学习参考，请结合自身情况决策")
