import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import akshare as ak
import warnings
import numpy as np
from collections import Counter

warnings.filterwarnings('ignore')

# ==================== 页面配置 ====================
st.set_page_config(page_title="股票量价分析器", layout="wide", page_icon="📈")

st.title("🚀 股票量价智能分析器（专业版）")

# ==================== 缓存函数 ====================
@st.cache_data(ttl=3600)  # 缓存1小时
def get_symbol(user_input):
    user_input = str(user_input).strip().upper()
    # 如果已经是带后缀的代码，直接返回
    if any(x in user_input for x in ['.SH', '.SZ', '.SS', '.HK']):
        return user_input.replace('.SS', '.SH')
    
    try:
        code_df = ak.stock_info_a_code_name()
        match = code_df[code_df['name'].str.contains(user_input, na=False)]
        if not match.empty:
            code = str(match.iloc[0]['code'])
            if code.startswith(('0', '3', '8')):
                return f"{code}.SZ"
            else:
                return f"{code}.SH"
    except:
        pass
    return user_input


@st.cache_data(ttl=1800)  # 缓存30分钟
def get_stock_data(symbol, days):
    try:
        df = yf.Ticker(symbol).history(period=f"{days + 60}d")
        if df.empty:
            return None
        return df.tail(days).copy()
    except:
        return None


# ==================== 技术指标计算 ====================
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
        user_input = st.text_input("股票名称或代码", value="300058", help="支持中文名称或代码搜索")
        days = st.slider("分析天数", min_value=5, max_value=180, value=30, step=1)
        analyze_button = st.button("🚀 开始专业分析", type="primary")
    else:
        st.info("当前为多只股票对比模式")
        compare_input = st.text_area("请输入多只股票（每行一个）", 
                                   value="000768\n300058\n蓝色光标", 
                                   height=120)
        compare_button = st.button("🚀 开始多只股票对比", type="primary")

# ==================== 单只股票分析 ====================
if not compare_mode and analyze_button and user_input:
    with st.spinner(f"正在获取并分析 {user_input}（近{days}日）..."):
        try:
            symbol = get_symbol(user_input)
            df = get_stock_data(symbol, days)
            
            if df is None or len(df) < 10:
                st.error(f"无法获取 {user_input} 的数据，请尝试其他股票或稍后重试")
                st.stop()

            # 数据清洗
            df = df.ffill()

            # 计算指标
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
            df['K'], df['D'], df['J'] = calculate_kdj(df)
            df['BB_Middle'], df['BB_Upper'], df['BB_Lower'] = calculate_bbands(df)

            # RSI
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
            
            vp_count = Counter(vp_types)
            latest_vp = vp_types[-1] if vp_types else '量价中性'

            # 评分
            score = 5.0
            if latest['Close'] > latest['MA5']: score += 1.0
            if latest['J'] > 80: score -= 1.0
            if latest_vp == '价涨量增': score += 1.5
            final_score = min(10, max(1, round(score, 1)))

            # ==================== 图表 ====================
            fig = make_subplots(rows=5, cols=1,
                              subplot_titles=(f"价格 + 布林带（近{days}日）", "MACD", "KDJ", "RSI", "成交量"),
                              row_heights=[0.30, 0.18, 0.17, 0.15, 0.20], 
                              vertical_spacing=0.05)

            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(width=2.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='布林上轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Middle'], name='布林中轨', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='布林下轨', line=dict(dash='dot')), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='DIF'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='DEA'), row=2, col=1)
            colors = ['red' if h > 0 else 'green' for h in df['Hist']]
            fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name='MACD柱', marker_color=colors), row=2, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['J'], name='J'), row=3, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=3, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI(14)', line=dict(color='purple', width=2)), row=4, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)

            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='skyblue'), row=5, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='量MA5'), row=5, col=1)

            fig.update_layout(height=1250, title_text=f"{user_input}（{symbol}） 近{days}日量价分析")
            st.plotly_chart(fig, use_container_width=True)

            # ==================== 分析报告 ====================
            st.subheader("📋 专业分析报告")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新价格", f"{latest['Close']:.2f}")
            with col2:
                change = ((latest['Close'] / df.iloc[0]['Close']) - 1) * 100
                st.metric("区间涨跌幅", f"{change:.2f}%")
            with col3:
                st.metric("综合评分", f"{final_score}/10")

            st.subheader("🔍 研判要点")
            points = []
            if latest['Close'] < latest.get('MA5', latest['Close']):
                points.append("• 短期均线在下，偏空")
            if latest_vp == '价涨量增':
                points.append("• 最新出现价涨量增，资金关注度提升")
            if latest['J'] > 70:
                points.append("• KDJ-J 值偏高，短期有回调风险")
            if latest['RSI'] < 30:
                points.append("• RSI处于超卖区，注意反弹机会")
            elif latest['RSI'] > 70:
                points.append("• RSI处于超买区，注意回调风险")

            if points:
                for p in points:
                    st.write(p)
            else:
                st.write("• 当前多空信号交织，建议观望")

            st.subheader("📊 近10日明细")
            recent = df[['Close', 'Volume', 'Volume_Ratio', 'Vol_Anomaly']].tail(10).copy()
            recent['涨跌幅%'] = df['Close'].pct_change().tail(10) * 100
            st.dataframe(recent.round(2), use_container_width=True)

            st.subheader("💡 综合买卖建议")
            if final_score >= 8:
                st.success("✅ **偏多信号较强，可考虑分批买入**")
            elif final_score >= 6:
                st.info("🟡 **多空交织，建议观望或轻仓操作**")
            else:
                st.warning("⚠️ **偏空信号较多，建议保持谨慎**")

        except Exception as e:
            st.error(f"分析失败: {str(e)[:100]}")

# ==================== 多只股票对比模式 ====================
if compare_mode and compare_button:
    with st.spinner("正在进行多只股票对比分析..."):
        try:
            stocks = [line.strip() for line in compare_input.split('\n') if line.strip()]
            
            if len(stocks) < 2:
                st.warning("请至少输入2只股票进行对比")
            else:
                compare_data = {}
                metrics = {}
                
                for stock in stocks:
                    try:
                        sym = get_symbol(stock)
                        hist = yf.Ticker(sym).history(period="180d")
                        if len(hist) > 30:
                            close = hist['Close'].tail(90)
                            compare_data[stock] = (close / close.iloc[0] * 100).round(2)
                            
                            ret = (close.iloc[-1] / close.iloc[0] - 1) * 100
                            vol = close.pct_change().std() * 100
                            mdd = ((close / close.cummax()) - 1).min() * 100
                            
                            metrics[stock] = {
                                '区间收益率%': round(ret, 2),
                                '波动率%': round(vol, 2),
                                '最大回撤%': round(mdd, 2)
                            }
                    except:
                        st.warning(f"无法获取 {stock} 数据，已跳过")
                        continue
                
                if compare_data:
                    compare_df = pd.DataFrame(compare_data)
                    st.subheader("📈 归一化价格走势对比（起点=100）")
                    fig = go.Figure()
                    for col in compare_df.columns:
                        fig.add_trace(go.Scatter(x=compare_df.index, y=compare_df[col], name=col))
                    fig.update_layout(height=500, title="多只股票归一化价格对比")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.subheader("📊 关键指标对比（近90日）")
                    metrics_df = pd.DataFrame(metrics).T
                    st.dataframe(metrics_df.style.highlight_max(axis=0), use_container_width=True)
                    
                    st.success(f"✅ {len(compare_data)} 只股票对比完成！")
                else:
                    st.error("未能获取有效数据")
                    
        except Exception as e:
            st.error(f"对比失败: {str(e)[:80]}...")

st.caption("由 Grok 优化构建 | 仅供参考 | 数据来源于 yfinance & akshare")
