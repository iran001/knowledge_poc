"""
IHG智能问答平台 - 统一配置文件
"""

import os
from typing import Dict, Any, List

# =============================================================================
# 服务器配置
# =============================================================================
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "backend_port": 8000,
    "frontend_port": 8501,
    "reload": True
}

# =============================================================================
# Dify API 配置
# =============================================================================
DIFY_CONFIG = {
    "base_url": "http://116.62.30.61/v1",
    "chatbot_url": "http://116.62.30.61/chatbot/RgIwnnnxUrynbPCN",
    "timeout": 30
}

# =============================================================================
# RAGFlow API 配置
# =============================================================================
RAGFLOW_CONFIG = {
    "base_url": "http://localhost:9380",
    "api_key": "your-api-key-here",
    "timeout": 30
}

# =============================================================================
# 应用信息
# =============================================================================
APP_INFO = {
    "name": "IHG智能问答平台",
    "version": "1.0.0",
    "logo": "🤖",
    "description": "支持RBAC权限控制的AI知识管理系统"
}

# =============================================================================
# 页面配置
# =============================================================================
PAGE_CONFIG = {
    "login": {
        "title": "登录",
        "background_image": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=1920"
    },
    "chat": {
        "title": "智能对话",
        "welcome_message": "您好！我是IHG智能助手，请问有什么可以帮助您？"
    },
    "documents": {
        "title": "文档中心"
    },
    "hot_knowledge": {
        "title": "热知识管理"
    }
}

# =============================================================================
# 角色显示映射
# =============================================================================
ROLE_DISPLAY_MAP: Dict[str, Dict[str, Any]] = {
    "admin": {"name": "系统管理员", "color": "🔴", "desc": "拥有最高权限，可访问所有数据和配置"},
    "manager": {"name": "客服经理", "color": "🟠", "desc": "可访问标准文档和案例分析"},
    "reception": {"name": "前台", "color": "🟢", "desc": "仅可访问公开文档和基础问答"}
}

# =============================================================================
# 角色权限级别映射（用于RBAC）
# =============================================================================
ROLE_LEVEL_MAP = {
    "admin": 3,
    "manager": 2,
    "reception": 1
}

# =============================================================================
# 角色Prompt映射（用于动态注入）
# =============================================================================
ROLE_PROMPT_MAP = {
    "admin": """你是IHG酒店的系统管理员助手，拥有最高权限。
你可以访问所有文档和数据，包括财务信息、人事档案、系统配置等敏感内容。
请以专业、高效的方式回答管理员的问题。""",

    "manager": """你是IHG酒店的客服经理助手，拥有标准权限。
你可以访问标准操作文档、案例分析、客户反馈等资料。
请帮助经理处理客户投诉、分析服务问题、提供改进建议。""",

    "reception": """你是IHG酒店的前台助手，拥有基础权限。
你只能访问公开的操作手册、常见问题解答、酒店设施介绍等基础文档。
请友好地回答客人的咨询问题，帮助他们办理入住、了解酒店服务。"""
}

# =============================================================================
# Dify Chatbot Embed 配置（角色相关）
# =============================================================================

# Dify Chatbot 基础配置
DIFY_CHATBOT_CONFIG = {
    "base_url": "http://116.62.30.61",
    "token": "RgIwnnnxUrynbPCN"
}

# 角色对应的输入变量（传递给 Dify 工作流）
DIFY_ROLE_INPUTS_MAP: Dict[str, Dict[str, str]] = {
    "admin": {
        "role": "admin",
        "role_name": "系统管理员",
        "access_level": "high"
    },
    "manager": {
        "role": "manager",
        "role_name": "客服经理",
        "access_level": "medium"
    },
    "reception": {
        "role": "reception",
        "role_name": "前台接待",
        "access_level": "low"
    }
}

# 角色对应的系统变量（Dify 系统级配置）
DIFY_ROLE_SYSTEM_VARS_MAP: Dict[str, Dict[str, str]] = {
    "admin": {
        "user_type": "administrator",
        "permissions": "full_access"
    },
    "manager": {
        "user_type": "manager",
        "permissions": "standard_access"
    },
    "reception": {
        "user_type": "front_desk",
        "permissions": "limited_access"
    }
}

# 角色对应的用户变量（用户头像和显示名称）
DIFY_ROLE_USER_VARS_MAP: Dict[str, Dict[str, str]] = {
    "admin": {
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/295/295128.png",
        "name": "系统管理员"
    },
    "manager": {
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/295/295117.png",
        "name": "客服经理"
    },
    "reception": {
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/295/295105.png",
        "name": "前台接待"
    }
}

# =============================================================================
# 模板和静态文件目录
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# =============================================================================
# 模拟用户数据
# =============================================================================
MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password": "123456",
        "role": "admin",
        "display_name": "系统管理员"
    },
    "manager": {
        "username": "manager",
        "password": "123456",
        "role": "manager",
        "display_name": "客服经理"
    },
    "reception": {
        "username": "reception",
        "password": "123456",
        "role": "reception",
        "display_name": "前台接待"
    }
}

# =============================================================================
# 模拟文档数据（带权限级别）
# =============================================================================
MOCK_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "doc_001",
        "title": "酒店员工手册",
        "content": "包含所有员工的基本行为规范和操作流程，适用于所有员工。",
        "permission_level": 1,
        "category": "基础文档",
        "updated_at": "2024-01-15"
    },
    {
        "id": "doc_002",
        "title": "前台接待流程指南",
        "content": "详细说明前台接待客人的标准流程，包括入住、退房、咨询等环节。",
        "permission_level": 1,
        "category": "操作手册",
        "updated_at": "2024-01-20"
    },
    {
        "id": "doc_003",
        "title": "客户投诉处理案例集",
        "content": "收集整理了50个典型客户投诉案例及处理方案，供管理人员参考。",
        "permission_level": 2,
        "category": "案例分析",
        "updated_at": "2024-02-01"
    },
    {
        "id": "doc_004",
        "title": "月度财务报表分析",
        "content": "包含本月收入、支出、利润分析，以及各部门业绩对比。仅供管理层查看。",
        "permission_level": 3,
        "category": "财务数据",
        "updated_at": "2024-02-15"
    },
    {
        "id": "doc_005",
        "title": "员工绩效评估标准",
        "content": "详细的员工绩效考核标准和评估表，涉及薪酬调整等敏感信息。",
        "permission_level": 3,
        "category": "人事档案",
        "updated_at": "2024-02-10"
    }
]

# =============================================================================
# 模拟热知识数据
# =============================================================================
MOCK_HOT_KNOWLEDGE: List[Dict[str, Any]] = [
    {
        "id": "hot_001",
        "title": "VIP客人入住提醒",
        "content": "本周末有3位VIP客人入住，请前台特别关注并提前准备欢迎礼品。",
        "priority": "high",
        "added_at": "2024-03-10"
    },
    {
        "id": "hot_002",
        "title": "空调系统维护通知",
        "content": "3月15日凌晨2-4点将进行空调系统维护，届时部分区域可能受到影响。",
        "priority": "medium",
        "added_at": "2024-03-12"
    },
    {
        "id": "hot_003",
        "title": "新员工培训资料",
        "content": "本月入职的5名新员工培训资料已更新，请经理安排培训时间。",
        "priority": "low",
        "added_at": "2024-03-11"
    }
]

# =============================================================================
# Streamlit前端配置（仅在导入streamlit时使用）
# =============================================================================
try:
    import streamlit as st

    def init_page_config():
        """初始化页面配置"""
        st.set_page_config(
            page_title="IHG智能问答平台",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )

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

except ImportError:
    # 当streamlit未安装时（后端环境），提供空函数
    def init_page_config():
        pass

    def init_session_state():
        pass


# =============================================================================
# 前端全局常量配置
# =============================================================================
# 自动检测后端地址（支持同站点部署和独立部署）
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

