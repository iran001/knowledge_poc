"""
IHG智能问答平台 - Streamlit 前端主入口
"""

import streamlit as st
from config import init_page_config, init_session_state, ROLE_DISPLAY_MAP
from pages import render_login_page, render_chat_page, render_documents_page, render_hot_knowledge_page


# =============================================================================
# 初始化
# =============================================================================
init_page_config()
init_session_state()


# =============================================================================
# 页面组件
# =============================================================================

def render_page_structure():
    """
    渲染页面统一结构：
    1. 最上层：标题 "🤖 IHG智能问答平台"
    2. 左侧边栏：功能导航菜单 + 底部用户信息和退出按钮
    3. 右侧主区域：具体页面内容
    """
    if not st.session_state.authenticated:
        return

    user = st.session_state.current_user
    user_name = user.get('display_name', user.get('username'))
    role = st.session_state.user_role

    # ========== 第一层：标题区域 ==========
    st.markdown("<h1 style='margin: 0; padding: 0;'>🤖 IHG智能问答平台</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # ========== 第二层：左侧边栏导航 + 右侧内容区域 ==========
    with st.sidebar:
        st.subheader("功能导航")

        # 智能对话按钮
        chat_type = "primary" if st.session_state.page == "chat" else "secondary"
        if st.button("💬 智能对话", use_container_width=True, type=chat_type):
            st.session_state.page = "chat"
            st.rerun()

        # 文档中心按钮
        doc_type = "primary" if st.session_state.page == "documents" else "secondary"
        if st.button("📄 文档中心", use_container_width=True, type=doc_type):
            st.session_state.page = "documents"
            st.rerun()

        # 添加空白区域将用户信息和退出按钮推到底部
        st.markdown("<br>" * 10, unsafe_allow_html=True)

        # 底部用户信息和退出区域（相同样式）
        st.markdown("---")

        # 用户信息按钮样式（使用st.button保持样式一致，但禁用点击）
        st.button(f"👤 {user_name}", use_container_width=True, disabled=True, key="user_info_btn")

        # 退出登录按钮（相同样式）
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.session_state.page = "login"
            st.session_state.chat_history = []
            st.rerun()


# =============================================================================
# 主函数
# =============================================================================
def main():
    """主函数 - 页面路由控制"""
    # 页面路由
    if not st.session_state.authenticated:
        render_login_page()
    else:
        # 渲染统一页面结构
        render_page_structure()

        # 根据当前页面渲染具体内容
        page = st.session_state.page

        if page == "chat":
            render_chat_page()
        elif page == "documents":
            render_documents_page()
        elif page == "hot_knowledge":
            render_hot_knowledge_page()
        else:
            render_chat_page()  # 默认显示聊天页面


# =============================================================================
# 启动入口
# =============================================================================
if __name__ == "__main__":
    main()
