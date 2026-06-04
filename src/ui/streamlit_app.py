from __future__ import annotations

import streamlit as st

st.set_page_config(
  page_title="AI 求职决策工作台",
  page_icon="AI",
  layout="centered",
)

st.title("已切换到 Vue 版页面")
st.info("Streamlit 版不再作为主要界面。请使用 Vue 前端。")
st.write("推荐运行：")
st.code(
  "cd path\\to\\agent-implementation\n"
  "powershell -ExecutionPolicy Bypass -File .\\start_vue_ui.ps1",
  language="powershell",
)
st.write("然后打开：http://127.0.0.1:5175")
