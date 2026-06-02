import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta
import time
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**A股 · 美股 | 成交量异常检测**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768", help="A股示例：000768、600519\n美股示例：AAPL、TSLA")
    days = st.slider("分析天数", 10, 90, 30)
    analyze_button = st.button("🚀 开始分析", type="primary")

if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}（可能需要等待）..."):
        try:
            df = None
            # 多次重试 + 备用方案
            for attempt in range(6):
                try:
                    if any(x in symbol.upper() for x in ['.SZ','.SH','000','600','300','688']):
                        st.info(f"第 {attempt+1} 次尝试获取A股数据...")
                        df = ak.stock_zh_a_hist(symbol=symbol[:6], period="daily", 
                                              start_date=(datetime.now()-timedelta(days=days+100)).strftime('%Y%m%d'))
                    else:
                        df = yf.Ticker(symbol).history(period=f"{days+60}d")
                    
                    df = df.tail(days).copy()
                    if len(df) >= 10:
                        break
                except:
                    time.sleep(3)
            
            if len(df) < 10:
                st.error("A股数据暂时无法获取，建议尝试美股（如 AAPL）")
                st.stop()

            # 计算指标和绘图（保持不变）
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            df['Anomaly'] = '正常'
            df.loc[df['Volume'] > vol_mean * 2, 'Anomaly'] = '🔴 显著放量'
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            ax1.plot(df.index, df['Close'], label='收盘价')
            ax1.plot(df.index, df['MA5'], label='MA5')
            ax1.plot(df.index, df['MA10'], label='MA10')
            ax1.plot(df.index, df['MA20'], label='MA20')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            ax2.bar(df.index, df['Volume'], color='skyblue')
            ax2.set_ylabel('成交量')
            plt.tight_layout()
            st.pyplot(fig)
            
            latest = df.iloc[-1]
            st.metric("最新价格", f"{latest['Close']:.2f}")
            change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
            st.metric("期间涨跌幅", f"{change:+.2f}%")
            
            anomalies = df[df['Anomaly'] != '正常']
            if not anomalies.empty:
                st.warning(f"🚨 发现 {len(anomalies)} 天成交量异常")
                st.dataframe(anomalies[['Close', 'Volume', 'Anomaly']])
            else:
                st.success("✅ 近期成交量正常")
                
        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")
            st.info("A股数据源不稳定，建议多尝试几次或使用美股代码")

st.caption("由 Grok 构建 | A股数据有时不稳定")
