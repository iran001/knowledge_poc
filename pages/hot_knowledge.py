"""
热知识管理页面
"""

import streamlit as st
import requests
import os

# API 基础URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def api_add_hot_knowledge(role: str, title: str, content: str):
    """调用后端添加热知识接口（仅管理员）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/hot-knowledge?role={role}",
            json={"title": title, "content": content, "priority": "high"},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


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
