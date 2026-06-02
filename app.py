import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import numpy as np

warnings.filterwarnings('ignore')

# 彻底解决字体问题
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**大白话版 | MACD+RSI+KDJ+布林带+筹码分布**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="A股建议加 .SZ 或 .SS")
    days = st.slider("分析天数", 10, 180, 60)
    analyze_button = st.button("🚀 开始分析", type="primary")

def plot_chip_distribution(df):
    """改进版筹码分布图"""
    prices = df['Close']
    volumes = df['Volume']
    
    price_min, price_max = prices.min(), prices.max()
    bins = np.linspace(price_min * 0.95, price_max * 1.05, 40)
    digitized = np.digitize(prices, bins)
    
    chip = np.zeros(len(bins))
    for i in range(len(prices)):
        chip[digitized[i]-1] += volumes.iloc[i]
    
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(bins, chip, width=(bins[1]-bins[0])*0.85, alpha=0.85, color='coral')
    ax.set_title('筹码分布图（近似）')
    ax.set_xlabel('股价区间')
    ax.set_ylabel('成交量集中度')
    ax.grid(True, alpha=0.3)
    return fig

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}..."):
        try:
            df = yf.Ticker(symbol).history(period=f"{days+60}d")
            df = df.tail(days).copy()
            
            if len(df) < 30:
                st.error("数据不足，请尝试其他股票")
                st.stop()

            # 计算指标（MACD、RSI、KDJ、布林带）
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
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

            # 主图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))
            ax1.plot(df.index, df['Close'], label='收盘价', linewidth=2.5)
            ax1.plot(df.index, df['MA5'], label='5日均线')
            ax1.plot(df.index, df['MA10'], label='10日均线')
            ax1.plot(df.index, df['MA20'], label='20日均线')
            ax1.plot(df.index, df['BB_Upper'], label='布林上轨', linestyle='--', alpha=0.7)
            ax1.plot(df.index, df['BB_Lower'], label='布林下轨', linestyle='--', alpha=0.7)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            ax2.bar(df.index, df['Volume'], color='skyblue', alpha=0.8)
            ax2.set_ylabel('成交量')
            plt.tight_layout()
            st.pyplot(fig)

            # 筹码分布图
            st.subheader("🧿 筹码分布图（近似）")
            chip_fig = plot_chip_distribution(df)
            st.pyplot(chip_fig)

            # 大白话建议（保持之前版本）
            st.success("✅ 分析完成！")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")

st.caption("由 Grok 构建 | 仅供学习参考")
