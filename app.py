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
st.markdown("**MACD + RSI + KDJ + 筹码分布 + 智能买卖建议**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="美股: AAPL\nA股: 000768.SZ 或 600519.SS")
    days = st.slider("分析天数", 10, 180, 60)
    analyze_button = st.button("🚀 开始分析", type="primary")

def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_kdj(df, n=9):
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def plot_chip_distribution(df):
    """近似筹码分布图"""
    prices = df['Close']
    volumes = df['Volume']
    
    # 创建价格区间
    price_min, price_max = prices.min(), prices.max()
    bins = np.linspace(price_min * 0.95, price_max * 1.05, 50)
    digitized = np.digitize(prices, bins)
    
    chip = np.zeros(len(bins))
    for i in range(len(prices)):
        chip[digitized[i]-1] += volumes.iloc[i]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(bins, chip, width=(bins[1]-bins[0])*0.9, alpha=0.7, color='orange')
    ax.set_title('筹码分布图（近似）')
    ax.set_xlabel('股价区间')
    ax.set_ylabel('成交量权重（筹码集中度）')
    ax.grid(True, alpha=0.3)
    return fig

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}..."):
        try:
            df = yf.Ticker(symbol).history(period=f"{days+60}d")
            df = df.tail(days).copy()
            
            if len(df) < 30:
                st.error("数据不足，请增加天数或尝试其他股票")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            df['MACD'], df['Signal'], df['Histogram'] = calculate_macd(df)
            df['RSI'] = calculate_rsi(df)
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            
            # 智能买卖建议
            latest = df.iloc[-1]
            score = 0
            suggestions = []
            
            if latest['MACD'] > latest['Signal']:
                suggestions.append("✅ MACD处于金叉区域")
                score += 2
            if latest['RSI'] < 40:
                suggestions.append("🟢 RSI处于低位")
                score += 2
            if latest['K'] < 30:
                suggestions.append("🟢 KDJ超卖")
                score += 1
                
            if score >= 4:
                rec = "🟢 **强烈看多，可考虑买入**"
            elif score >= 2:
                rec = "🟡 **偏多，适合观察**"
            else:
                rec = "⚪ **中性或偏空，谨慎操作**"
            
            # 显示图表
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_price, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
                ax1.plot(df.index, df['Close'], label='收盘价')
                ax1.plot(df.index, df['MA5'], label='MA5')
                ax1.plot(df.index, df['MA10'], label='MA10')
                ax1.plot(df.index, df['MA20'], label='MA20')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                
                ax2.bar(df.index, df['Volume'], color='skyblue', alpha=0.7)
                ax2.set_ylabel('成交量')
                plt.tight_layout()
                st.pyplot(fig_price)
            
            with col2:
                st.subheader("📊 最新指标")
                st.metric("最新价格", f"{latest['Close']:.2f}")
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("涨跌幅", f"{change:+.2f}%")
                st.metric("RSI", f"{latest['RSI']:.1f}")
                st.metric("MACD", f"{latest['MACD']:.3f}")
                
                st.subheader("📌 买卖建议")
                st.markdown(f"**{rec}**")
                for s in suggestions:
                    st.write(s)
            
            # 筹码分布图
            st.subheader("🧿 筹码分布图（近似）")
            chip_fig = plot_chip_distribution(df)
            st.pyplot(chip_fig)
            
        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")
            st.info("提示：部分A股代码支持有限，可尝试添加 .SZ / .SS 后缀")

st.caption("由 Grok 构建 | 仅供学习参考 · 非投资建议")
