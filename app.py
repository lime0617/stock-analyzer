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
st.markdown("**支持A股 · 美股 · 成交量异常检测 · 自动邮件报告**")

# 侧边栏
with st.sidebar:
    st.header("📊 分析设置")
    symbol = st.text_input("股票代码", value="000768", help="A股示例: 000768、600519  美股示例: AAPL、TSLA")
    days = st.slider("分析周期（交易日）", min_value=10, max_value=90, value=30)
    
    st.subheader("📧 邮件报告")
    enable_email = st.checkbox("分析完成后发送邮件", value=True)
    to_email = st.text_input("接收邮箱", value="19129547967@163.com")
    
    analyze_button = st.button("🚀 开始分析", type="primary")

def get_email_config():
    return {
        "user": st.secrets.get("EMAIL_USER", ""),
        "password": st.secrets.get("EMAIL_PASS", ""),
        "to": to_email,
        "smtp_server": "smtp.163.com",
        "smtp_port": 465
    }

def send_analysis_email(to_email, symbol, df, chart_path, days):
    config = get_email_config()
    if not config["password"]:
        st.warning("⚠️ 未配置邮箱密码（请在 Streamlit Secrets 设置）")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = config["user"]
    msg['To'] = to_email
    msg['Subject'] = f"【量价分析报告】{symbol} - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"""
{symbol} 近 {days} 日量价分析报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
最新收盘：{df['Close'].iloc[-1]:.2f}
期间涨跌幅：{((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100):+.2f}%
    """
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    if os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(chart_path)}')
            msg.attach(part)
    
    try:
        with smtplib.SMTP_SSL(config["smtp_server"], config["smtp_port"]) as server:
            server.login(config["user"], config["password"])
            server.sendmail(config["user"], to_email, msg.as_string())
        st.success(f"✅ 报告已发送至 {to_email}")
        return True
    except Exception as e:
        st.error(f"❌ 邮件发送失败: {e}")
        return False

# 分析逻辑
if analyze_button and symbol:
    with st.spinner(f"正在获取 {symbol} 数据..."):
        try:
            # === 超级稳定数据获取 ===
            df = None
            for attempt in range(5):
                try:
                    if any(x in symbol.upper() for x in ['.SZ','.SH','.BJ','000','600','300','688']):
                        df = ak.stock_zh_a_hist(
                            symbol=symbol[:6], 
                            period="daily",
                            start_date=(datetime.now()-timedelta(days=days+90)).strftime('%Y%m%d')
                        )
                        df = df.rename(columns={'日期':'Date', '收盘':'Close', '成交量':'Volume', 
                                              '开盘':'Open', '最高':'High', '最低':'Low'})
                        df['Date'] = pd.to_datetime(df['Date'])
                        df = df.set_index('Date')
                    else:
                        df = yf.Ticker(symbol).history(period=f"{days+60}d")
                    
                    df = df.tail(days).copy()
                    if len(df) >= 5:
                        break
                except:
                    if attempt < 4:
                        time.sleep(3 + attempt)
                    else:
                        raise
            
            if df is None or len(df) < 5:
                st.error("数据获取失败，请稍后重试或尝试其他股票")
                st.info("提示：A股有时不稳定，可尝试美股 AAPL / TSLA 测试")
                return

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            vol_mean = df['Volume'].mean()
            vol_std = df['Volume'].std()
            df['Volume_Z'] = (df['Volume'] - vol_mean) / vol_std
            df['Anomaly'] = '正常'
            df.loc[df['Volume_Z'] > 2.0, 'Anomaly'] = '🔴 显著放量'
            df.loc[df['Volume_Z'] < -1.5, 'Anomaly'] = '🔵 显著缩量'
            
            # 绘图
            fig_path = f"{symbol}_chart.png"
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
            
            ax1.plot(df.index, df['Close'], label='收盘价', linewidth=2)
            ax1.plot(df.index, df['MA5'], label='MA5')
            ax1.plot(df.index, df['MA10'], label='MA10')
            ax1.plot(df.index, df['MA20'], label='MA20')
            ax1.set_title(f'{symbol} 近 {days} 个交易日 量价分析')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            colors = ['red' if v > vol_mean else 'green' for v in df['Volume']]
            ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7)
            ax2.set_ylabel('成交量')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(fig_path, dpi=200, bbox_inches='tight')
            
            # 显示结果
            col1, col2 = st.columns([3, 2])
            with col1:
                st.pyplot(fig)
            with col2:
                st.subheader("📊 关键指标")
                latest = df.iloc[-1]
                st.metric("最新价格", f"{float(latest['Close']):.2f}")
                
                try:
                    change = ((float(latest['Close']) / float(df.iloc[0]['Close']) - 1) * 100)
                    st.metric("期间涨跌幅", f"{change:+.2f}%")
                except:
                    st.metric("期间涨跌幅", "计算错误")
                
                anomalies = df[df['Anomaly'] != '正常']
                if not anomalies.empty:
                    st.warning(f"🚨 发现 {len(anomalies)} 天成交量异常")
                    st.dataframe(anomalies[['Close', 'Volume', 'Anomaly']])
                else:
                    st.success("✅ 近期成交量无显著异常")
            
            if enable_email:
                send_analysis_email(to_email, symbol, df, fig_path, days)
            
            if os.path.exists(fig_path):
                os.remove(fig_path)
                
        except Exception as e:
            st.error(f"分析失败: {str(e)[:120]}")
            st.info("建议稍等几分钟后再试，或尝试美股代码")

st.caption("数据来源：akshare + yfinance | 由 Grok 构建")
