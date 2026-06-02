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
st.markdown("**近30日量价 + 板块 + 十大股东 + 机构持仓 + 涨停统计 + 年报 + 增减持**")

with st.sidebar:
    st.header("分析设置")
    user_input = st.text_input("股票名称或代码", value="000768", help="支持名称（如中航西飞）或代码")
    analyze_button = st.button("🚀 开始全景分析", type="primary")

@st.cache_data(ttl=300)
def get_stock_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="90d")
        return df
    except:
        return None

def get_stock_sector(code):
    try:
        pure_code = code.split('.')[0]
        info = ak.stock_individual_info_em(symbol=pure_code)
        if not info.empty:
            possible_names = ['所属行业', '行业', '所属板块', '板块', '主营业务']
            for name in possible_names:
                sector_row = info[info['item'].str.contains(name, na=False, regex=False)]
                if not sector_row.empty:
                    return sector_row['value'].values[0]
            return info.iloc[0]['value'] if len(info) > 0 else "未知板块"
        return "未知板块"
    except:
        return "未知板块"

def get_top10_shareholders(code):
    """十大股东（使用更稳定的接口）"""
    try:
        pure_code = code.split('.')[0]
        # 优先使用自由流通股十大股东
        df = ak.stock_gdfx_free_top_10_em(symbol=pure_code)
        if df is not None and not df.empty:
            latest_date = df['公告日'].max()
            df_latest = df[df['公告日'] == latest_date][['股东名称', '持股数(万股)', '持股比例(%)', '增减']]
            return df_latest.head(10)
        return None
    except:
        return None

def get_institution_hold(code):
    """机构持仓（最新季度）"""
    try:
        pure_code = code.split('.')[0]
        df = ak.stock_institution_hold_detail(symbol=pure_code)
        if df is not None and not df.empty:
            latest = df.iloc[0]
            return {
                '季度': latest.get('报告期', '未知'),
                '机构数': latest.get('机构数', '未知'),
                '持股数(万股)': latest.get('持股数', '未知'),
                '持股比例(%)': latest.get('持股比例', '未知')
            }
        return None
    except:
        return None

def get_limit_up_stats(code, days=90):
    """近90日涨停统计"""
    try:
        pure_code = code.split('.')[0]
        df = ak.stock_zh_a_hist(symbol=pure_code, period="daily", adjust="qfq")
        df = df.tail(days + 5).copy()
        df['涨跌幅'] = df['收盘'].pct_change() * 100
        df['是否涨停'] = (df['涨跌幅'] >= 9.5) & (df['收盘'] == df['最高'])
        
        limit_up_days = df[df['是否涨停']].copy()
        limit_up_count = len(limit_up_days)
        
        next_day_perf = []
        for idx in limit_up_days.index:
            if idx + 1 < len(df):
                next_ret = df.iloc[idx + 1]['涨跌幅']
                next_day_perf.append(next_ret)
        
        avg_next = round(np.mean(next_day_perf), 2) if next_day_perf else 0
        up_prob = round(sum(1 for x in next_day_perf if x > 0) / len(next_day_perf) * 100, 1) if next_day_perf else 0
        
        return {
            '涨停次数': limit_up_count,
            '次日平均涨跌幅': avg_next,
            '次日上涨概率': up_prob
        }
    except:
        return None

def get_financial_summary(code):
    """年报关键指标"""
    try:
        pure_code = code.split('.')[0]
        df = ak.stock_financial_abstract(symbol=pure_code)
        if df is not None and not df.empty:
            latest = df.iloc[0]
            return {
                '报告期': latest.get('报告期', '未知'),
                '营业收入(亿)': latest.get('营业收入', '未知'),
                '净利润(亿)': latest.get('净利润', '未知'),
                '营收同比': latest.get('营业收入同比', '未知'),
                '净利润同比': latest.get('净利润同比', '未知')
            }
        return None
    except:
        return None

def get_holder_change(code):
    """最近增减持"""
    try:
        pure_code = code.split('.')[0]
        df = ak.stock_gdfx_free_holding_change_em(symbol=pure_code)
        if df is not None and not df.empty:
            return df.head(5)[['股东名称', '增减持股数(万股)', '增减持股比例(%)', '增减持开始日']]
        return None
    except:
        return None

if analyze_button and user_input:
    with st.spinner(f"正在进行 {user_input} 全景分析..."):
        try:
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

            # 获取数据
            sector = get_stock_sector(symbol)
            top10_df = get_top10_shareholders(symbol)
            inst_hold = get_institution_hold(symbol)
            limit_up = get_limit_up_stats(symbol)
            financial = get_financial_summary(symbol)
            holder_change = get_holder_change(symbol)

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

            # 板块
            st.subheader("🏭 所属板块")
            st.info(f"**{sector}**")

            # 十大股东
            st.subheader("👥 十大股东（最新一期）")
            if top10_df is not None and not top10_df.empty:
                st.dataframe(top10_df, use_container_width=True, hide_index=True)
            else:
                st.warning("暂未获取到十大股东数据（可能需稍后重试）")

            # 机构持仓
            st.subheader("🏦 机构持仓（最新季度）")
            if inst_hold:
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a: st.metric("季度", inst_hold.get('季度', '未知'))
                with col_b: st.metric("机构数", inst_hold.get('机构数', '未知'))
                with col_c: st.metric("持股数(万股)", inst_hold.get('持股数(万股)', '未知'))
                with col_d: st.metric("持股比例(%)", inst_hold.get('持股比例(%)', '未知'))
            else:
                st.warning("暂未获取到机构持仓数据（可能需稍后重试）")

            # 涨停统计
            st.subheader("📈 近90日涨停统计")
            if limit_up:
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("涨停次数", limit_up['涨停次数'])
                with col2: st.metric("次日平均涨跌幅", f"{limit_up['次日平均涨跌幅']}%")
                with col3: st.metric("次日上涨概率", f"{limit_up['次日上涨概率']}%")
            else:
                st.warning("暂未获取到涨停统计数据")

            # 年报关键指标
            st.subheader("📊 年报关键指标（最新）")
            if financial:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("报告期", financial.get('报告期', '未知'))
                with col2: st.metric("营业收入(亿)", financial.get('营业收入(亿)', '未知'))
                with col3: st.metric("净利润(亿)", financial.get('净利润(亿)', '未知'))
                with col4: st.metric("净利润同比", financial.get('净利润同比', '未知'))
            else:
                st.warning("暂未获取到年报数据")

            # 增减持
            st.subheader("🔄 最近增减持情况")
            if holder_change is not None and not holder_change.empty:
                st.dataframe(holder_change, use_container_width=True, hide_index=True)
            else:
                st.warning("暂未获取到增减持数据")

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
