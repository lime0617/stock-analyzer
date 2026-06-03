import streamlit as st
import os

# Railway 环境适配
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = os.environ.get("PORT", "8080")
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_BROWSER_GATHERUSAGESTATS"] = "false"

st.set_page_config(page_title="股票分析器", layout="wide")

st.title("🚀 测试页面 - 如果看到这个就成功了")
st.success("✅ 服务已正常运行！")

st.info("现在你可以把完整代码逐步加回来测试。")
