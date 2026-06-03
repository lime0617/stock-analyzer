import os
import streamlit as st

# === Railway / Server 环境优化 ===
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = os.environ.get("PORT", "8080")
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_BROWSER_GATHERUSAGESTATS"] = "false"

# 防止启动时报错
st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")
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
st.title("🚀 股票量价智能分析器（短线专业版）")

# ==================== 超强名称转代码 ====================
@st.cache_data(ttl=3600)
def get_symbol(user_input):
    if not user_input:
        return user_input
    user_input = str(user_input).strip()
    upper = user_input.upper()

    if user_input.isdigit() and len(user_input) == 6:
        if user_input.startswith(('6', '5', '9')):
            return f"{user_input}.SH"
        else:
            return f"{user_input}.SZ"

    if any(x in upper for x in ['.SH', '.SZ', '.SS', '.HK']):
        return upper.replace('.SS', '.SH')

    name_map = {
        "华电辽能": "600396", "辽能": "600396", "华电": "600396",
        "贵州茅台": "600519", "茅台": "600519",
        "宁德时代": "300750", "宁德": "300750",
        "比亚迪": "002594",
        "中国平安": "601318", "平安": "601318",
        "招商银行": "600036", "招行": "600036",
        "五粮液": "000858",
        "隆基绿能": "601012", "隆基": "601012",
        "蓝色光标": "300058", "光标": "300058",
        "中航沈飞": "600760", "沈飞": "600760",
        "长江电力": "600900",
        "中国神华": "601088",
        "万科": "000002", "万科A": "000002",
        "华安证券": "600909",
    }
    for key in name_map:
        if key in user_input or key in upper:
            code = name_map[key]
            return f"{code}.SH" if code.startswith(('6','9')) else f"{code}.SZ"

    try:
        df = ak.stock_info_a_code_name()
        match = df[df['name'].str.contains(user_input, case=False, na=False)]
        if not match.empty:
            code = str(match.iloc[0]['code'])
            return f"{code}.SH" if code.startswith(('6','9')) else f"{code}.SZ"
    except:
        pass
    return user_input


@st.cache_data(ttl=1800)
def get_stock_data(symbol, days):
    code = symbol[:6] if len(symbol) >= 6 else symbol
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        if not df.empty:
            df = df.set_index('日期')
            df = df.rename(columns={'开盘':'Open','收盘':'Close','最高':'High','最低':'Low','成交量':'Volume'})
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            return df.tail(days + 40).tail(days)
    except:
        pass
    try:
        df = yf.Ticker(symbol).history(period=f"{days + 60}d")
        if not df.empty:
            return df.tail(days)
    except:
        pass
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

def calculate_psy(df, period=12):
    diff = df['Close'].diff()
    up = (diff > 0).rolling(window=period).sum()
    return up / period * 100

def calculate_bias(df, period=6):
    ma = df['Close'].rolling(window=period).mean()
    return (df['Close'] - ma) / ma * 100

def calculate_cci(df, period=14):
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    ma_tp = tp.rolling(window=period).mean()
    md = tp.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
    return (tp - ma_tp) / (0.015 * md)

def calculate_obv(df):
    obv = (df['Volume'] * (df['Close'] > df['Close'].shift(1)).astype(int) * 2 - 1).cumsum()
    return obv

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_wr(df, period=14):
    highest_high = df['High'].rolling(window=period).max()
    lowest_low = df['Low'].rolling(window=period).min()
    wr = -100 * (highest_high - df['Close']) / (highest_high - lowest_low)
    return wr

# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("分析设置")
    compare_mode = st.checkbox("开启多只股票对比模式", value=False)
  
    if not compare_mode:
        user_input = st.text_input("股票名称或代码", value="600396", help="推荐直接输入6位代码")
        days = st.slider("分析天数", min_value=5, max_value=180, value=30, step=1)
        analyze_button = st.button("🚀 开始短线专业分析", type="primary")
    else:
        st.info("当前为多只股票对比模式")
        compare_input = st.text_area("请输入多只股票（每行一个）", value="600396\n300058\n600519", height=120)
        compare_button = st.button("🚀 开始多只股票对比", type="primary")

# ==================== 单只股票分析 ====================
if not compare_mode and analyze_button and user_input:
    with st.spinner(f"正在获取并分析 {user_input}..."):
        try:
            symbol = get_symbol(user_input)
            df = get_stock_data(symbol, days)
            
            if df is None or len(df) < 20:
                st.error(f"无法获取 **{user_input}** 的数据\n\n**建议**：直接输入6位股票代码（如 600396）")
                st.stop()

            df = df.ffill()

            # 计算所有指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            df['BB_Middle'], df['BB_Upper'], df['BB_Lower'] = calculate_bbands(df)
            df['PSY'] = calculate_psy(df)
            df['BIAS'] = calculate_bias(df)
            df['CCI'] = calculate_cci(df)
            df['OBV'] = calculate_obv(df)
            df['ATR'] = calculate_atr(df)
            df['WR'] = calculate_wr(df)

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

            # 100分制评分
            score = 50.0
            if latest['Close'] > latest['MA5']: score += 8
            if latest['Close'] > latest['MA10']: score += 7
            if latest['Close'] > latest['BB_Middle']: score += 10
            if latest['MACD'] > latest['Signal']: score += 12
            if latest['MACD'] > 0: score += 8
            if latest['J'] < 35: score += 10
            elif latest['J'] > 75: score -= 10
            if latest['K'] > latest['D']: score += 5
            if 25 < latest['PSY'] < 75: score += 8
            elif latest['PSY'] > 75: score -= 10
            elif latest['PSY'] < 25: score += 12
            if abs(latest['BIAS']) < 5: score += 7
            elif latest['BIAS'] < -8: score += 10
            elif latest['BIAS'] > 8: score -= 10
            if -100 < latest['CCI'] < 100: score += 5
            elif latest['CCI'] < -100: score += 8
            elif latest['CCI'] > 100: score -= 8
            if latest['WR'] < -80: score += 10
            elif latest['WR'] > -20: score -= 8
            if latest_vp == '价涨量增': score += 12
            elif latest_vp == '价涨量缩': score -= 8

            final_score = max(10, min(100, round(score)))

            # ==================== 图表 ====================
            fig = make_subplots(rows=6, cols=1,
                              subplot_titles=("价格 + 布林带", "MACD", "KDJ", "情绪指标(PSY+CCI)", "OBV+成交量", "WR威廉指标"),
                              row_heights=[0.22, 0.16, 0.16, 0.16, 0.15, 0.15], vertical_spacing=0.04)

            # 1. 价格 + 布林带
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='布林上轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Middle'], name='布林中轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='布林下轨', line=dict(dash='dot')), row=1, col=1)

            # 2. MACD
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='DIF'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='DEA'), row=2, col=1)
            colors = ['red' if h > 0 else 'green' for h in df['Hist']]
            fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name='MACD柱', marker_color=colors), row=2, col=1)

            # 3. KDJ
            fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['J'], name='J'), row=3, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=3, col=1)

            # 4. 情绪指标
            fig.add_trace(go.Scatter(x=df.index, y=df['PSY'], name='PSY(12)', line=dict(color='orange')), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['CCI'], name='CCI(14)', line=dict(color='purple')), row=4, col=1)
            fig.add_hline(y=75, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=25, line_dash="dash", line_color="green", row=4, col=1)
            fig.add_hline(y=100, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=-100, line_dash="dash", line_color="green", row=4, col=1)

            # 5. OBV + 成交量
            fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name='OBV', line=dict(color='purple')), row=5, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=5, col=1)

            # 6. WR威廉指标
            fig.add_trace(go.Scatter(x=df.index, y=df['WR'], name='WR(14)', line=dict(color='brown')), row=6, col=1)
            fig.add_hline(y=-20, line_dash="dash", line_color="red", row=6, col=1)
            fig.add_hline(y=-80, line_dash="dash", line_color="green", row=6, col=1)

            fig.update_layout(height=1550, title_text=f"{user_input}（{symbol}） 短线多指标分析")
            st.plotly_chart(fig, use_container_width=True)

            # ==================== 报告 ====================
            st.subheader("📋 短线分析报告")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2: st.metric("区间涨跌幅", f"{((latest['Close'] / df.iloc[0]['Close']) - 1) * 100:.2f}%")
            with col3: st.metric("短线综合得分", f"{final_score} 分")

            st.subheader("🚦 技术信号灯")
            sig1, sig2, sig3, sig4 = st.columns(4)
            with sig1:
                if latest['Close'] > latest['BB_Middle']: st.success("📈 布林带：多头")
                else: st.error("📉 布林带：空头")
            with sig2:
                if latest['MACD'] > latest['Signal']: st.success("📈 MACD：金叉")
                else: st.error("📉 MACD：死叉")
            with sig3:
                if latest['J'] < 35: st.success("📈 KDJ：超卖")
                elif latest['J'] > 75: st.error("📉 KDJ：超买")
                else: st.info("➡️ KDJ：中性")
            with sig4:
                if latest_vp == '价涨量增': st.success("📈 量价：强势")
                elif latest_vp == '价涨量缩': st.warning("⚠️ 量价：乏力")
                else: st.info("➡️ 量价：正常")

            st.subheader("🌡️ 市场情绪指标")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                psy_val = latest['PSY']
                if psy_val > 75: st.error(f"PSY: {psy_val:.1f}（过热）")
                elif psy_val < 25: st.success(f"PSY: {psy_val:.1f}（恐慌）")
                else: st.info(f"PSY: {psy_val:.1f}")
            with col_b:
                bias_val = latest['BIAS']
                if bias_val > 8: st.error(f"BIAS: {bias_val:.1f}（高估）")
                elif bias_val < -8: st.success(f"BIAS: {bias_val:.1f}（低估）")
                else: st.info(f"BIAS: {bias_val:.1f}")
            with col_c:
                cci_val = latest['CCI']
                if cci_val > 100: st.error(f"CCI: {cci_val:.1f}（超买）")
                elif cci_val < -100: st.success(f"CCI: {cci_val:.1f}（超卖）")
                else: st.info(f"CCI: {cci_val:.1f}")

            st.subheader("💡 短线操作建议")
            if final_score >= 78:
                st.success("🔥 **强烈短线买入** - 多指标共振")
            elif final_score >= 65:
                st.success("✅ **可短线参与**")
            elif final_score >= 50:
                st.info("🟡 **观望等待更好时机**")
            else:
                st.error("❌ **短期风险较高，建议暂不操作**")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:150]}")

st.caption("短线专业版 | OBV+WR+ATR+PSY+CCI | 推荐输入6位代码 | 仅供参考")
