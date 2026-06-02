import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
from datetime import datetime, timedelta
import warnings
import numpy as np

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器")
st.markdown("**近30日量价 + 板块 + 大白话解读 + 买卖建议**")

with st.sidebar:
    st.header("分析设置")
    user_input = st.text_input("股票名称或代码", value="000768", help="支持名称（如中航西飞）或代码")
    analyze_button = st.button("🚀 开始分析", type="primary")

@st.cache_data(ttl=300)
def get_stock_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="60d")
        return df.tail(30)
    except:
        return None

def get_stock_sector(code):
    """获取所属板块（增强兼容性）"""
    try:
        pure_code = code.split('.')[0]
        info = ak.stock_individual_info_em(symbol=pure_code)
        
        if not info.empty:
            # 尝试匹配常见字段名
            possible_names = ['所属行业', '行业', '所属板块', '板块', '主营业务']
            for name in possible_names:
                sector_row = info[info['item'].str.contains(name, na=False, regex=False)]
                if not sector_row.empty:
                    return sector_row['value'].values[0]
            
            # 如果都没匹配到，返回第一条有意义的信息
            return info.iloc[0]['value'] if len(info) > 0 else "未知板块"
        
        return "未知板块"
    except Exception as e:
        return f"获取失败"

if analyze_button and user_input:
    with st.spinner(f"正在分析 {user_input}..."):
        try:
            # 自动处理名称/代码
            symbol = user_input
            if not any(x in user_input.upper() for x in ['.SZ', '.SH', '.SS']):
                try:
                    code_df = ak.stock_info_a_code_name()
                    match = code_df[code_df['name'].str.contains(user_input, na=False)]
                    if not match.empty:
                        code = match.iloc[0]['code']
                        symbol = f"{code}.SZ" if code.startswith(('0', '3')) else f"{code}.SS"
                except:
                    pass

            df = get_stock_data(symbol)
            if df is None or len(df) < 20:
                st.error("数据获取失败，请检查股票代码或稍后重试")
                st.stop()

            # 计算指标
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
            if latest['Close'] > latest['MA5']:
                score += 1.5
            if latest['RSI'] < 40:
                score += 2.0
            if latest['Volume_Ratio'] > 1.5:
                score += 1.5
            final_score = min(10, max(1, round(score, 1)))

            # 获取板块
            sector = get_stock_sector(symbol)

            # ==================== 展示 ====================
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = (latest['Close'] / df.iloc[0]['Close'] - 1) * 100
                st.metric("近30日涨跌幅", f"{change:+.2f}%")
            with col3:
                st.metric("综合评分", f"{final_score} / 10 分")

            # 主图表
            st.subheader(f"{user_input} 近30日量价分析")
            fig = make_subplots(rows=3, cols=1, subplot_titles=("价格走势", "成交量", "RSI"), row_heights=[0.5, 0.3, 0.2])
            
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], name='10日均线'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日均线'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
            
            fig.update_layout(height=800)
            st.plotly_chart(fig, use_container_width=True)

            # 板块信息
            st.subheader("🏭 所属板块")
            st.info(f"**{sector}**")

            # 筹码分布
            st.subheader("🧿 筹码分布图（近似）")
            prices = df['Close']
            volumes = df['Volume']
            bins = np.linspace(prices.min()*0.95, prices.max()*1.05, 40)
            digitized = np.digitize(prices, bins)
            chip = np.zeros(len(bins))
            for i in range(len(prices)):
                chip[digitized[i]-1] += volumes.iloc[i]
            
            fig_chip = go.Figure(go.Bar(x=bins, y=chip, marker_color='coral'))
            fig_chip.update_layout(title="成交量在不同价格区间的集中度", 
                                 xaxis_title="股价区间", yaxis_title="成交量权重", height=400)
            st.plotly_chart(fig_chip, use_container_width=True)

            # 大白话总结
            st.subheader("📋 大白话总结")
            st.metric("综合评分", f"{final_score} / 10 分")
            
            if final_score >= 8:
                st.success("🔥 **近期表现较强，值得重点关注**")
            elif final_score >= 6:
                st.info("🟡 **表现中等，可继续观察**")
            else:
                st.warning("⚪ **目前表现一般，建议谨慎**")

            st.subheader("💡 买卖建议")
            if final_score >= 8:
                st.success("✅ **建议考虑分批买入**（趋势较好）")
            elif final_score >= 6.5:
                st.info("🟡 **可以观察，回调时可分批买入**")
            else:
                st.warning("⚠️ **暂不建议重仓**，等待更好时机")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}... 请稍后重试")

st.caption("由 Grok 构建 | 支持名称搜索 | 仅供参考")
