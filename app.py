import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
import warnings
import numpy as np

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器（专业版）")
st.markdown("**近30日量价 + MACD/KDJ/布林带 + 量价形态 + 异常检测**")

with st.sidebar:
    st.header("分析设置")
    user_input = st.text_input("股票名称或代码", value="300058", help="支持名称搜索")
    analyze_button = st.button("🚀 开始专业分析", type="primary")

def get_symbol(user_input):
    if any(x in user_input.upper() for x in ['.SZ', '.SH', '.SS']):
        return user_input
    try:
        code_df = ak.stock_info_a_code_name()
        match = code_df[code_df['name'].str.contains(user_input, na=False)]
        if not match.empty:
            code = match.iloc[0]['code']
            return f"{code}.SZ" if code.startswith(('0', '3')) else f"{code}.SS"
    except:
        pass
    return user_input

def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist

def calculate_kdj(df, n=9):
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def calculate_bbands(df, window=20):
    sma = df['Close'].rolling(window=window).mean()
    std = df['Close'].rolling(window=window).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return sma, upper, lower

if analyze_button and user_input:
    with st.spinner(f"正在进行专业分析 {user_input}..."):
        try:
            symbol = get_symbol(user_input)
            df = yf.Ticker(symbol).history(period="60d").tail(30).copy()

            if len(df) < 20:
                st.error("数据不足")
                st.stop()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            df['BB_Middle'], df['BB_Upper'], df['BB_Lower'] = calculate_bbands(df)

            vol_mean = df['Volume'].mean()
            vol_std = df['Volume'].std()
            df['Volume_Ratio'] = df['Volume'] / vol_mean
            df['Vol_Anomaly'] = '正常'
            df.loc[df['Volume'] > vol_mean + 2*vol_std, 'Vol_Anomaly'] = '放量异常'
            df.loc[df['Volume'] < vol_mean - 1.5*vol_std, 'Vol_Anomaly'] = '缩量异常'

            latest = df.iloc[-1]

            # 量价形态统计
            vp_types = []
            for i in range(1, len(df)):
                prev_close = df['Close'].iloc[i-1]
                curr_close = df['Close'].iloc[i]
                prev_vol = df['Volume'].iloc[i-1]
                curr_vol = df['Volume'].iloc[i]
                if curr_close > prev_close and curr_vol > prev_vol:
                    vp_types.append('价涨量增')
                elif curr_close < prev_close and curr_vol < prev_vol:
                    vp_types.append('价跌量缩')
                elif curr_close > prev_close and curr_vol < prev_vol:
                    vp_types.append('价涨量缩')
                else:
                    vp_types.append('量价中性')
            
            from collections import Counter
            vp_count = Counter(vp_types)
            latest_vp = vp_types[-1] if vp_types else '量价中性'

            # 评分
            score = 5.0
            if latest['Close'] > latest['MA5']: score += 1.0
            if latest['RSI'] < 40 if 'RSI' in df.columns else False: score += 1.5
            if latest_vp == '价涨量增': score += 1.5
            if latest['J'] > 80: score -= 1.0
            final_score = min(10, max(1, round(score, 1)))

            # ==================== 图表 ====================
            fig = make_subplots(rows=4, cols=1, 
                              subplot_titles=("价格 + 布林带", "MACD", "KDJ", "成交量"),
                              row_heights=[0.35, 0.25, 0.2, 0.2], vertical_spacing=0.08)

            # 价格 + 布林带
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='布林上轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Middle'], name='布林中轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='布林下轨', line=dict(dash='dot')), row=1, col=1)

            # MACD
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='DIF'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='DEA'), row=2, col=1)
            colors = ['red' if h > 0 else 'green' for h in df['Hist']]
            fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name='MACD柱', marker_color=colors), row=2, col=1)

            # KDJ
            fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['J'], name='J'), row=3, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=3, col=1)

            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='量MA5'), row=4, col=1)

            fig.update_layout(height=1100, title_text=f"{user_input} 近30日量价 + 技术指标分析")
            st.plotly_chart(fig, use_container_width=True)

            # ==================== 结构化报告 ====================
            st.subheader("📋 专业分析报告")

            col1, col2, col3 = st.columns(3)
            with col1: st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2: st.metric("区间涨跌幅", f"{((latest['Close']/df.iloc[0]['Close'])-1)*100:.2f}%")
            with col3: st.metric("综合评分", f"{final_score}/10")

            st.write("**量价形态统计**：", dict(vp_count))
            st.write("**最新量价类型**：", latest_vp)
            st.write("**放量异常天数**：", len(df[df['Vol_Anomaly'] == '放量异常']))
            st.write("**缩量异常天数**：", len(df[df['Vol_Anomaly'] == '缩量异常']))

            st.subheader("研判要点")
            if latest['Close'] < latest['MA5']:
                st.write("• 短期均线在下，偏空")
            if latest_vp == '价涨量增':
                st.write("• 最新出现价涨量增，资金关注度提升")
            if latest['J'] > 70:
                st.write("• KDJ-J 偏高，短期有回调风险")

            st.subheader("综合买卖建议")
            if final_score >= 8:
                st.success("✅ **偏多信号较强，可考虑分批买入**")
            elif final_score >= 6:
                st.info("🟡 **多空交织，建议观望或轻仓**")
            else:
                st.warning("⚠️ **偏空信号较多，建议谨慎**")

            # 近10日明细
            st.subheader("近10日明细")
            recent = df[['Close', 'Volume', 'Volume_Ratio', 'Vol_Anomaly']].tail(10).copy()
            recent['涨跌幅%'] = df['Close'].pct_change().tail(10) * 100
            st.dataframe(recent.round(2), use_container_width=True)

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}...")

st.caption("由 Grok 构建 | 专业版 | 仅供参考")
