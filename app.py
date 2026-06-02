import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**纯 yfinance 版本 | MACD + RSI + KDJ + 成交量异常**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768.SZ", help="美股: AAPL\nA股: 000768.SZ 或 600519.SS")
    days = st.slider("分析天数", 10, 120, 30)
    analyze_button = st.button("🚀 开始分析", type="primary")

def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_kdj(df, n=9, m1=3, m2=3):
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}..."):
        try:
            # 数据获取
            df = yf.Ticker(symbol).history(period=f"{days+60}d")
            df = df.tail(days).copy()
            
            if len(df) < 20:
                st.error("数据不足，请尝试其他股票或增加天数")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            # MACD
            df['MACD'], df['Signal'], df['Histogram'] = calculate_macd(df)
            
            # RSI
            df['RSI'] = calculate_rsi(df)
            
            # KDJ
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            
            # 成交量异常
            vol_mean = df['Volume'].mean()
            df['Anomaly'] = '正常'
            df.loc[df['Volume'] > vol_mean * 2, 'Anomaly'] = '🔴 显著放量'
            df.loc[df['Volume'] < vol_mean * 0.5, 'Anomaly'] = '🔵 显著缩量'
            
            # 绘图
            fig = plt.figure(figsize=(14, 10))
            
            # 价格 + MACD
            ax1 = plt.subplot(4, 1, 1)
            ax1.plot(df.index, df['Close'], label='收盘价', linewidth=2)
            ax1.plot(df.index, df['MA5'], label='MA5')
            ax1.plot(df.index, df['MA10'], label='MA10')
            ax1.plot(df.index, df['MA20'], label='MA20')
            ax1.set_title(f'{symbol} 技术指标分析')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # MACD
            ax2 = plt.subplot(4, 1, 2)
            ax2.plot(df.index, df['MACD'], label='MACD', color='blue')
            ax2.plot(df.index, df['Signal'], label='Signal', color='red')
            ax2.bar(df.index, df['Histogram'], label='Histogram', color=['green' if x > 0 else 'red' for x in df['Histogram']])
            ax2.set_ylabel('MACD')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # RSI
            ax3 = plt.subplot(4, 1, 3)
            ax3.plot(df.index, df['RSI'], label='RSI(14)', color='purple')
            ax3.axhline(70, color='red', linestyle='--')
            ax3.axhline(30, color='green', linestyle='--')
            ax3.set_ylabel('RSI')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 成交量 + KDJ
            ax4 = plt.subplot(4, 1, 4)
            ax4.bar(df.index, df['Volume'], color='skyblue', alpha=0.7)
            ax4.set_ylabel('成交量')
            ax4_twin = ax4.twinx()
            ax4_twin.plot(df.index, df['K'], label='K', color='blue')
            ax4_twin.plot(df.index, df['D'], label='D', color='orange')
            ax4_twin.plot(df.index, df['J'], label='J', color='red')
            ax4_twin.legend()
            
            plt.tight_layout()
            st.pyplot(fig)
            
            # 关键指标展示
            col1, col2, col3 = st.columns(3)
            latest = df.iloc[-1]
            
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("期间涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("RSI", f"{latest['RSI']:.1f}")
            
            st.subheader("技术指标最新值")
            st.write(f"**MACD**: {latest['MACD']:.3f} | **Signal**: {latest['Signal']:.3f}")
            st.write(f"**KDJ**: K={latest['K']:.1f} | D={latest['D']:.1f} | J={latest['J']:.1f}")
            
            # 异常
            anomalies = df[df['Anomaly'] != '正常']
            if not anomalies.empty:
                st.warning(f"🚨 发现 {len(anomalies)} 天成交量异常")
                st.dataframe(anomalies[['Close', 'Volume', 'Anomaly']])
            
        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")
            st.info("提示：部分A股代码支持有限，推荐使用 .SZ / .SS 后缀")

st.caption("纯 yfinance 版本 | MACD + RSI + KDJ | 由 Grok 构建")
