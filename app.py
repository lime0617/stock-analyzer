import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
import warnings
from collections import Counter

warnings.filterwarnings('ignore')

st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")
st.title("🚀 股票量价智能分析器（专业版）")

# ==================== 缓存函数 ====================
@st.cache_data(ttl=3600)
def get_symbol(user_input):
    user_input = str(user_input).strip().upper()
    if any(x in user_input for x in ['.SH', '.SZ', '.SS', '.HK']):
        return user_input.replace('.SS', '.SH')
    
    try:
        code_df = ak.stock_info_a_code_name()
        match = code_df[code_df['name'].str.contains(user_input, na=False)]
        if not match.empty:
            code = str(match.iloc[0]['code'])
            return f"{code}.SZ" if code.startswith(('0', '3', '8')) else f"{code}.SH"
    except:
        pass
    return user_input


@st.cache_data(ttl=1800)
def get_stock_data(symbol, days):
    try:
        df = yf.Ticker(symbol).history(period=f"{days + 60}d")
        return df.tail(days).copy() if not df.empty else None
    except:
        return None


# ==================== 技术指标 ====================
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


# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("分析设置")
    compare_mode = st.checkbox("开启多只股票对比模式", value=False)
  
    if not compare_mode:
        user_input = st.text_input("股票名称或代码", value="300058", help="支持中文名称搜索")
        days = st.slider("分析天数", min_value=5, max_value=180, value=30, step=1)
        analyze_button = st.button("🚀 开始专业分析", type="primary")
    else:
        st.info("当前为多只股票对比模式")
        compare_input = st.text_area("请输入多只股票（每行一个）", value="000768\n300058\n蓝色光标", height=120)
        compare_button = st.button("🚀 开始多只股票对比", type="primary")

# ==================== 单只股票分析 ====================
if not compare_mode and analyze_button and user_input:
    with st.spinner(f"正在分析 {user_input}（近{days}日）..."):
        try:
            symbol = get_symbol(user_input)
            df = get_stock_data(symbol, days)
            
            if df is None or len(df) < 10:
                st.error(f"无法获取 {user_input} 的数据，请尝试其他股票")
                st.stop()

            df = df.ffill()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            df['BB_Middle'], df['BB_Upper'], df['BB_Lower'] = calculate_bbands(df)

            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs.fillna(0)))

            # 量价分析
            vol_mean = df['Volume'].mean()
            vol_std = df['Volume'].std()
            df['Volume_Ratio'] = df['Volume'] / vol_mean
            df['Vol_Anomaly'] = '正常'
            df.loc[df['Volume'] > vol_mean + 2*vol_std, 'Vol_Anomaly'] = '放量异常'
            df.loc[df['Volume'] < vol_mean - 1.5*vol_std, 'Vol_Anomaly'] = '缩量异常'

            latest = df.iloc[-1]

            # 量价形态
            vp_types = []
            for i in range(1, len(df)):
                p_close = df['Close'].iloc[i-1]
                c_close = df['Close'].iloc[i]
                p_vol = df['Volume'].iloc[i-1]
                c_vol = df['Volume'].iloc[i]
                if c_close > p_close and c_vol > p_vol:
                    vp_types.append('价涨量增')
                elif c_close < p_close and c_vol < p_vol:
                    vp_types.append('价跌量缩')
                elif c_close > p_close and c_vol < p_vol:
                    vp_types.append('价涨量缩')
                else:
                    vp_types.append('量价中性')
            
            latest_vp = vp_types[-1] if vp_types else '量价中性'

            # ==================== 100分制综合评分 ====================
            score = 50.0
            if latest['Close'] > latest['MA5']: score += 8
            if latest['Close'] > latest['MA10']: score += 7
            if latest['Close'] > latest['BB_Middle']: score += 10
            if latest['Close'] > latest['BB_Lower']: score += 5
            if latest['MACD'] > latest['Signal']: score += 12
            if latest['MACD'] > 0: score += 8
            if latest['J'] < 30: score += 10
            elif latest['J'] > 80: score -= 12
            if latest['K'] > latest['D']: score += 8
            if latest['RSI'] < 35: score += 10
            elif latest['RSI'] > 70: score -= 10
            elif 45 < latest['RSI'] < 55: score += 5
            if latest_vp == '价涨量增': score += 12
            elif latest_vp == '价跌量缩': score += 6
            elif latest_vp == '价涨量缩': score -= 8

            final_score = max(10, min(100, round(score)))

            # ==================== 图表 ====================
            fig = make_subplots(rows=5, cols=1,
                              subplot_titles=(f"价格 + 布林带（近{days}日）", "MACD", "KDJ", "RSI", "成交量"),
                              row_heights=[0.30, 0.18, 0.17, 0.15, 0.20], vertical_spacing=0.05)

            # 价格 + 布林带
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
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

            # RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI(14)', line=dict(color='purple', width=2)), row=4, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)

            # 成交量 + MA5
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=5, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='量MA5', line=dict(color='red')), row=5, col=1)

            fig.update_layout(height=1250, title_text=f"{user_input}（{symbol}） 近{days}日量价分析")
            st.plotly_chart(fig, use_container_width=True)

            # ==================== 报告 ====================
            st.subheader("📋 专业分析报告")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2: 
                change = ((latest['Close'] / df.iloc[0]['Close']) - 1) * 100
                st.metric("区间涨跌幅", f"{change:.2f}%")
            with col3: 
                st.metric("综合强度", f"{final_score} 分")

            # ==================== 技术信号灯 ====================
            st.subheader("🚦 技术信号灯")
            sig1, sig2, sig3, sig4 = st.columns(4)
            with sig1:
                if latest['Close'] > latest['BB_Middle']:
                    st.success("📈 布林带：多头")
                else:
                    st.error("📉 布林带：空头")
            with sig2:
                if latest['MACD'] > latest['Signal']:
                    st.success("📈 MACD：金叉")
                else:
                    st.error("📉 MACD：死叉")
            with sig3:
                if latest['J'] < 30:
                    st.success("📈 KDJ：超卖")
                elif latest['J'] > 80:
                    st.error("📉 KDJ：超买")
                else:
                    st.info("➡️ KDJ：中性")
            with sig4:
                if latest_vp == '价涨量增':
                    st.success("📈 量价：强势")
                elif latest_vp == '价涨量缩':
                    st.warning("⚠️ 量价：乏力")
                else:
                    st.info("➡️ 量价：正常")

            # ==================== 买卖建议 ====================
            st.subheader("💡 综合买卖建议")
            if final_score >= 80:
                st.success("🔥 **强烈买入信号** - 多指标共振")
            elif final_score >= 70:
                st.success("✅ **可考虑分批买入**")
            elif final_score >= 55:
                st.info("🟡 **观望为主**，等待更好时机")
            elif final_score >= 40:
                st.warning("⚠️ **谨慎操作**，风险较高")
            else:
                st.error("❌ **建议观望或减仓** - 空头信号较强")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}")

st.caption("由 Grok 优化构建 | 100分制评分 + 信号灯 | 仅供参考")
