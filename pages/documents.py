"""
文档中心页面
"""

import streamlit as st
import requests
import os

# API 基础URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def api_get_documents(role: str, keyword: str = ""):
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
