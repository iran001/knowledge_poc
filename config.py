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
# Dify API 配置："api_key": "app-eMP8p1e8UcjxdNBZymXc0LdX",
# =============================================================================
DIFY_CONFIG = {
    "base_url": "http://116.62.30.61/v1",
    "api_key": "app-eMP8p1e8UcjxdNBZymXc0LdX",
    "workflow_api_key": "app-AvE4LlNMgeuI3Q2OKryvcluj",
    "chat_messages_endpoint": "/chat-messages",
    "filecheck_endpoint": "/workflows/6ba4cfeb-fb68-4e7d-824e-76f68cda29ac/run",
    "upload_endpoint": "/files/upload",
    "timeout": 30
}

# =============================================================================
# RAGFlow API 配置
# =============================================================================
RAGFLOW_CONFIG = {
    "base_url": "http://118.31.184.47/api/v1",
    "api_key": "ragflow-VhZTNjNWY0ZGIxMjExZjBiMjg3NWE4Yj",
    "dataset_id": "31f6e5b81e1411f18dd4e67a6a3f482a",
    "vl_dataset_id": "9e91232c04e811f18c9e0664f063c4fe",
    "special_dataset_id": "3c521b90074b11f1826d0664f063c4fe",
    "timeout": 30,
    "page_size": 10
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
    "chat": {"title": "智能对话"},
    "documents": {"title": "文档中心"},
    "knowledge_upload": {"title": "文件上传"}
}

# =============================================================================
# 角色配置（合并显示、权限、Prompt、Dify输入变量）
# =============================================================================
ROLES: Dict[str, Dict[str, Any]] = {
    "admin": {
        "display_name": "系统管理员",
        "color": "🔴",
        "description": "拥有最高权限，可访问所有数据和配置",
        "level": 3,
        "prompt": """你是IHG酒店的系统管理员助手，拥有最高权限。
你可以访问所有文档和数据，包括财务信息、人事档案、系统配置等敏感内容。
请以专业、高效的方式回答管理员的问题。""",
        "dify_inputs": {"role": "admin", "role_name": "系统管理员", "access_level": "high"}
    },
    "manager": {
        "display_name": "客服经理",
        "color": "🟠",
        "description": "可访问标准文档和案例分析",
        "level": 2,
        "prompt": """你是IHG酒店的客服经理助手，拥有标准权限。
你可以访问标准操作文档、案例分析、客户反馈等资料。
请帮助经理处理客户投诉、分析服务问题、提供改进建议。""",
        "dify_inputs": {"role": "manager", "role_name": "客服经理", "access_level": "medium"}
    },
    "reception": {
        "display_name": "前台",
        "color": "🟢",
        "description": "仅可访问公开文档和基础问答",
        "level": 1,
        "prompt": """你是IHG酒店的前台助手，拥有基础权限。
你只能访问公开的操作手册、常见问题解答、酒店设施介绍等基础文档。
请友好地回答客人的咨询问题，帮助他们办理入住、了解酒店服务。""",
        "dify_inputs": {"role": "reception", "role_name": "前台接待", "access_level": "low"}
    }
}

# 兼容旧代码的映射（从 ROLES 派生）
ROLE_DISPLAY_MAP = {k: {"name": v["display_name"], "color": v["color"], "desc": v["description"]} for k, v in ROLES.items()}
ROLE_LEVEL_MAP = {k: v["level"] for k, v in ROLES.items()}
ROLE_PROMPT_MAP = {k: v["prompt"] for k, v in ROLES.items()}
DIFY_ROLE_INPUTS_MAP = {k: v["dify_inputs"] for k, v in ROLES.items()}

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
# 模拟文件数据
# =============================================================================
MOCK_KNOWLEDGE_UPLOAD: List[Dict[str, Any]] = [
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
# 前端全局常量配置
# =============================================================================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# =============================================================================
# Dify 已上传文件记录（自动生成的文件 ID 映射）
# 文件名 -> Dify file_id
# =============================================================================
DIFY_UPLOADED_FILES: Dict[str, str] = {
    "洲际酒店-B2B支付解决方案CN.txt": "44b32150-b1bb-4d01-a37a-a7ff47456abb"
}
