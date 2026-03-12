"""
登录页面
"""

import streamlit as st
import os

# API 基础URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def render_login_page():
    """渲染登录页面 - 使用iframe嵌入后端登录页面模板"""
    
    # 隐藏Streamlit默认元素，全屏显示登录页面
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 使用iframe嵌入后端登录页面（加载templates/login.html模板）
    st.markdown(f"""
    <iframe
        src="{API_BASE_URL}/"
        style="width: 100%; height: 100vh; border: none; position: fixed; top: 0; left: 0;"
        frameborder="0"
        allow="fullscreen">
    </iframe>
    """, unsafe_allow_html=True)
