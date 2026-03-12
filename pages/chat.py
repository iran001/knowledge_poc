"""
智能对话页面
"""

import streamlit as st
import os

# Dify 聊天机器人URL
DIFY_CHATBOT_URL = os.environ.get("DIFY_CHATBOT_URL", "http://116.62.30.61/chatbot/RgIwnnnxUrynbPCN")


def render_chat_page():
    """
    渲染智能对话页面
    使用 iframe 嵌入 Dify 聊天机器人
    """
    # 嵌入 Dify 聊天机器人 iframe，高度适配屏幕
    st.markdown(f"""
    <iframe
        src="{DIFY_CHATBOT_URL}"
        style="width: 100%; height: 65vh; border: none;"
        frameborder="0"
        allow="microphone">
    </iframe>
    """, unsafe_allow_html=True)
