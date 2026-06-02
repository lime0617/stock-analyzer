import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**纯 yfinance 版本 | 美股 & A股（部分支持） | 更稳定**")

with st.sidebar:
    st.header("分析设置")
    symbol = st.text_input("股票代码", value="000768", help="美股: AAPL, TSLA\nA股: 000768.SZ, 600519.SS")
    days = st.slider("分析天数", 10, 90, 30)
    analyze_button = st.button("🚀 开始分析", type="primary")

if analyze_button and symbol:
    with st.spinner(f"正在从 yfinance 获取 {symbol} 数据..."):
        try:
            # 处理A股代码格式
            yf_symbol = symbol
            if '.' not in symbol:
                if symbol.startswith(('000', '300', '688')):
                    yf_symbol = symbol + ".SZ"
                elif symbol.startswith(('600', '601', '603')):
                    yf_symbol = symbol + ".SS"
            
            df = yf.Ticker(yf_symbol).history(period=f"{days+60}d")
            df = df.tail(days).copy()
            
            if len(df) < 10:
                st.error("数据获取失败，请检查股票代码或稍后重试")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            df['Anomaly'] = '正常'
            df.loc[df['Volume'] > vol_mean * 2, 'Anomaly'] = '🔴 显著放量'
            df.loc[df['Volume'] < vol_mean * 0.5, 'Anomaly'] = '🔵 显著缩量'
            
            # 绘图
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            ax1.plot(df.index, df['Close'], label='收盘价', linewidth=2)
            ax1.plot(df.index, df['MA5'], label='MA5')
            ax1.plot(df.index, df['MA10'], label='MA10')
            ax1.plot(df.index, df['MA20'], label='MA20')
            ax1.set_title(f'{symbol} 近 {days} 个交易日量价分析')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            colors = ['red' if v > vol_mean else 'green' for v in df['Volume']]
            ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7)
            ax2.set_ylabel('成交量')
            plt.tight_layout()
            
            st.pyplot(fig)
            
            # 关键指标
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
            st.error(f"分析失败: {str(e)[:120]}")
            st.info("提示：A股部分代码支持有限，推荐使用 .SZ / .SS 后缀")

st.caption("纯 yfinance 版本 | 更稳定 | 由 Grok 构建")
