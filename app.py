import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import akshare as ak
import yfinance as yf
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import warnings
import time

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**支持A股 · 美股 · 成交量异常检测**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768")
    days = st.slider("分析天数", 10, 90, 30)
    enable_email = st.checkbox("发送邮件报告", value=False)
    to_email = st.text_input("接收邮箱", value="19129547967@163.com")
    
    analyze_button = st.button("开始分析", type="primary")

# ====================== 主逻辑 ======================
if analyze_button and symbol:
    with st.spinner(f"正在分析 {symbol}..."):
        try:
            # 数据获取（带重试）
            df = None
            for attempt in range(5):
                try:
                    if any(x in symbol.upper() for x in ['.SZ','.SH','000','600','300','688']):
                        df = ak.stock_zh_a_hist(symbol=symbol[:6], period="daily", 
                                              start_date=(datetime.now()-timedelta(days=days+90)).strftime('%Y%m%d'))
                        df = df.rename(columns={'日期':'Date', '收盘':'Close', '成交量':'Volume'})
                        df['Date'] = pd.to_datetime(df['Date'])
                        df = df.set_index('Date')
                    else:
                        df = yf.Ticker(symbol).history(period=f"{days+60}d")
                    df = df.tail(days).copy()
                    break
                except:
                    if attempt < 4:
                        time.sleep(3)
                    else:
                        raise
            
            if len(df) < 5:
                st.error("无法获取足够数据，请稍后重试")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            df['Anomaly'] = '正常'
            df.loc[(df['Volume'] > vol_mean * 2), 'Anomaly'] = '🔴 显著放量'
            
            # 绘图
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
            
            # 结果展示
            latest = df.iloc[-1]
            st.metric("最新价格", f"{latest['Close']:.2f}")
            change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
            st.metric("期间涨跌幅", f"{change:+.2f}%")
            
            anomalies = df[df['Anomaly'] != '正常']
            if not anomalies.empty:
                st.warning(f"发现 {len(anomalies)} 天成交量异常")
                st.dataframe(anomalies[['Close', 'Volume', 'Anomaly']])
            
            st.success("分析完成！")
            
        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")
            st.info("建议：尝试美股 AAPL 或稍等几分钟再试")

st.caption("由 Grok 构建 | 数据来源: akshare + yfinance")
