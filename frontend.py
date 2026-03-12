"""
AI知识管理平台 - Streamlit 前端
实现登录认证、角色权限展示、智能对话和文档管理
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

# =============================================================================
# 页面配置
# =============================================================================
st.set_page_config(
    page_title="AI知识管理平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 全局常量配置
# =============================================================================
# 自动检测后端地址（支持同站点部署和独立部署）
import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")  # FastAPI 后端地址

# 角色显示映射
ROLE_DISPLAY_MAP = {
    "admin": {"name": "系统管理员", "color": "🔴", "desc": "拥有最高权限，可访问所有数据和配置"},
    "manager": {"name": "客服经理", "color": "🟠", "desc": "可访问标准文档和案例分析"},
    "reception": {"name": "前台", "color": "🟢", "desc": "仅可访问公开文档和基础问答"}
}

# =============================================================================
# Session State 初始化
# =============================================================================
def init_session_state():
    """初始化 Streamlit Session State"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "documents" not in st.session_state:
        st.session_state.documents = []

init_session_state()

# =============================================================================
# API 调用封装
# =============================================================================

def api_login(username: str, password: str) -> Dict[str, Any]:
    """调用后端登录接口"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/login",
            json={"username": username, "password": password},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"网络错误: {str(e)}"}


def api_chat(role: str, message: str) -> Dict[str, Any]:
    """调用后端聊天接口（由后端转发到Dify）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={"role": role, "message": message},
            timeout=60
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


def api_get_documents(role: str, keyword: str = "") -> Dict[str, Any]:
    """调用后端文档列表接口"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/documents",
            json={"role": role, "search_keyword": keyword if keyword else None},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


def api_add_hot_knowledge(role: str, title: str, content: str) -> Dict[str, Any]:
    """调用后端添加热知识接口（仅管理员）"""
    try:
        # 使用GET参数传递role（简化实现）
        response = requests.post(
            f"{API_BASE_URL}/api/hot-knowledge?role={role}",
            json={"title": title, "content": content, "priority": "high"},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


# =============================================================================
# 页面组件
# =============================================================================

def render_page_structure():
    """
    渲染页面统一结构：
    1. 最上层：标题 "🤖 AI知识管理平台"
    2. 左侧边栏：功能导航菜单 + 底部用户信息和退出按钮
    3. 右侧主区域：具体页面内容
    """
    if not st.session_state.authenticated:
        return

    user = st.session_state.current_user
    user_name = user.get('display_name', user.get('username'))
    role = st.session_state.user_role

    # ========== 第一层：标题区域 ==========
    st.markdown("<h1 style='margin: 0; padding: 0;'>🤖 AI知识管理平台</h1>", unsafe_allow_html=True)
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

    # ========== 右侧主区域：页面内容（由各个页面函数渲染）==========


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
    



def render_chat_page():
    """
    渲染智能对话页面
    使用 iframe 嵌入 Dify 聊天机器人
    """
    # 嵌入 Dify 聊天机器人 iframe，高度适配屏幕
    st.markdown("""
    <iframe
        src="http://116.62.30.61/chatbot/RgIwnnnxUrynbPCN"
        style="width: 100%; height: 65vh; border: none;"
        frameborder="0"
        allow="microphone">
    </iframe>
    """, unsafe_allow_html=True)


def render_documents_page():
    """
    渲染文档列表页面
    【权限展示】不同角色看到不同权限级别的文档
    """
    role = st.session_state.user_role

    # 搜索栏 + 热知识管理入口（仅管理员）
    if role == "admin":
        # 管理员：搜索框 + 搜索按钮 + 热知识管理按钮 一行显示
        search_cols = st.columns([4, 1, 1.5])
        with search_cols[0]:
            search_keyword = st.text_input("搜索文档", placeholder="输入关键词搜索...", label_visibility="collapsed")
        with search_cols[1]:
            st.markdown("<div style='padding-top: 0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("🔍 搜索", use_container_width=True):
                st.rerun()
        with search_cols[2]:
            st.markdown("<div style='padding-top: 0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("🔥 热知识管理", use_container_width=True):
                st.session_state.page = "hot_knowledge"
                st.rerun()
    else:
        # 非管理员：只显示搜索框和搜索按钮
        search_cols = st.columns([4, 1])
        with search_cols[0]:
            search_keyword = st.text_input("搜索文档", placeholder="输入关键词搜索...", label_visibility="collapsed")
        with search_cols[1]:
            if st.button("🔍 搜索", use_container_width=True):
                st.rerun()

    # 获取文档列表
    with st.spinner("加载文档列表..."):
        result = api_get_documents(role, search_keyword)

    if result.get("success"):
        documents = result.get("documents", [])

        # 显示统计信息
        st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <span style="background: #e3f2fd; padding: 0.5rem 1rem; border-radius: 1rem;">
                共找到 <b>{len(documents)}</b> 个文档
            </span>
            <span style="background: #f3e5f5; padding: 0.5rem 1rem; border-radius: 1rem; margin-left: 0.5rem;">
                权限级别: <b>{result.get('visible_permission', '未知')}</b>
            </span>
        </div>
        """, unsafe_allow_html=True)

        if not documents:
            st.warning("没有找到符合条件的文档")
        else:
            # 权限标签样式
            permission_styles = {
                1: ("🟢 公开", "green"),
                2: ("🟠 内部", "orange"),
                3: ("🔴 敏感", "red")
            }

            # 显示文档卡片
            for doc in documents:
                perm_level = doc.get("permission_level", 1)
                perm_label, perm_color = permission_styles.get(perm_level, ("⚪ 未知", "gray"))

                with st.expander(f"📄 {doc.get('title', '未命名文档')}", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.markdown(f"**文档类型**: {doc.get('type', '未知')}")
                        st.markdown(f"**更新日期**: {doc.get('updated_at', '未知')}")

                    with col2:
                        st.markdown(f"**权限标签**: :{perm_color}[{perm_label}]")

                    with col3:
                        if st.button("查看详情", key=f"view_{doc.get('id')}"):
                            st.info(f"**文档内容预览**:\n\n{doc.get('content', '无内容')}")

                    # 显示文档内容（如果展开）
                    st.markdown("---")
                    st.markdown(f"**摘要**: {doc.get('content', '无内容')[:100]}...")

    else:
        st.error(f"获取文档失败: {result.get('message', '未知错误')}")


def render_hot_knowledge_page():
    """
    渲染热知识管理页面（独立页面）
    【管理员专属功能】
    """
    role = st.session_state.user_role

    # 权限检查
    if role != "admin":
        st.error("⛔ 权限不足！此功能仅系统管理员可用")
        st.info("您当前的角色无法访问此页面，请联系系统管理员")
        return

    # 返回文档中心链接
    if st.button("← 返回文档中心", key="back_to_docs"):
        st.session_state.page = "documents"
        st.rerun()
    st.markdown("---")

    # 两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("➕ 添加新热知识")

        with st.form("hot_knowledge_form"):
            title = st.text_input("标题", placeholder="输入热知识标题")
            content = st.text_area("内容", placeholder="输入热知识详细内容", height=150)
            priority = st.select_slider(
                "优先级",
                options=["low", "normal", "high"],
                value="normal"
            )

            submitted = st.form_submit_button("添加热知识", use_container_width=True, type="primary")

            if submitted:
                if title and content:
                    with st.spinner("保存中..."):
                        result = api_add_hot_knowledge(role, title, content)

                        if result.get("success"):
                            st.success("热知识添加成功！")
                        else:
                            st.error(f"添加失败: {result.get('message', '未知错误')}")
                else:
                    st.warning("请填写标题和内容")

    with col2:
        st.subheader("现有热知识")

        # 获取热知识列表
        try:
            response = requests.get(f"{API_BASE_URL}/api/hot-knowledge?role={role}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                knowledge_list = result.get("knowledge", [])

                if knowledge_list:
                    for item in knowledge_list:
                        with st.container():
                            st.markdown(f"""
                            <div style="
                                background: #fff3e0;
                                padding: 1rem;
                                border-radius: 0.5rem;
                                margin-bottom: 0.5rem;
                                border-left: 4px solid #ff9800;
                            ">
                                <h4>{item.get('title', '无标题')}</h4>
                                <p>{item.get('content', '无内容')[:80]}...</p>
                                <small>添加日期: {item.get('added_at', '未知')}</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("暂无热知识")
            else:
                st.warning("获取热知识列表失败")
        except Exception as e:
            st.error(f"请求失败: {str(e)}")


def main():
    """主函数 - 页面路由控制"""
    # 页面路由
    if not st.session_state.authenticated:
        render_login_page()
    else:
        # 渲染统一页面结构（三层：标题、导航、内容）
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
