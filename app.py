import os
import streamlit as st

# Railway 环境强制适配
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = os.environ.get("PORT", "8080")
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_BROWSER_GATHERUSAGESTATS"] = "false"

st.set_page_config(page_title="测试页面", layout="wide")

st.title("🚀 Streamlit 测试页面")
st.success("✅ 如果你看到这个页面，说明环境已经正常！")
st.info("现在可以逐步把你的原代码加回来测试。")

st.caption("Railway 部署测试 - 2026.06")
