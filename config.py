"""
IHG智能问答平台 - 配置文件
集中管理所有配置项
"""

import os
from typing import Dict, Any

# =============================================================================
# 基础配置
# =============================================================================

# 服务配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "backend_port": 8000,
    "frontend_port": 8501,
    "reload": False,
}

# 调试模式
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# =============================================================================
# 外部服务配置
# =============================================================================

# Dify API 配置
DIFY_CONFIG = {
    "base_url": "http://116.62.30.61/v1",
    "chatbot_url": "http://116.62.30.61/chatbot/RgIwnnnxUrynbPCN",
    "api_key": os.environ.get("DIFY_API_KEY", ""),  # 从环境变量读取
    "timeout": 60,
}

# RagFlow API 配置
RAGFLOW_CONFIG = {
    "base_url": "http://118.31.184.47/user-setting/api",
    "api_key": os.environ.get("RAGFLOW_API_KEY", ""),  # 从环境变量读取
    "timeout": 30,
}

# =============================================================================
# 角色与权限配置
# =============================================================================

# 角色类型
ROLE_TYPES = ["admin", "manager", "reception"]

# 角色显示映射
ROLE_DISPLAY_MAP = {
    "admin": {"name": "系统管理员", "color": "🔴", "desc": "拥有最高权限，可访问所有数据和配置"},
    "manager": {"name": "客服经理", "color": "🟠", "desc": "可访问标准文档和案例分析"},
    "reception": {"name": "前台", "color": "🟢", "desc": "仅可访问公开文档和基础问答"},
}

# 角色权限级别映射（数值越大权限越高）
ROLE_LEVEL_MAP = {
    "reception": 1,   # 前台 - 基础权限
    "manager": 2,     # 客服经理 - 中等权限
    "admin": 3        # 系统管理员 - 最高权限
}

# 【核心】角色-System Prompt 映射表
# 这是实现"基于角色的AI回答控制"的关键配置
ROLE_PROMPT_MAP = {
    "admin": """你是系统管理员助手。你可以访问所有层级数据，包括敏感配置和底层日志。
回答需专业、严谨，协助进行系统维护和策略制定。
你可以回答关于系统架构、数据库配置、安全策略等高级话题。
如果涉及关键操作，请提醒用户谨慎执行。""",

    "manager": """你是客服经理助手。你只能访问已发布的标准知识库和热点案例。
严禁回答关于系统底层架构、数据库密码或未审核的冲突内容。
回答需侧重于服务流程优化和案例分析。
你的职责是帮助客服经理提升团队服务质量和处理客户投诉。""",

    "reception": """你是前台接待助手。你只能回答基于公开文档的基础问题（如营业时间、基本政策）。
遇到复杂、模糊或涉及内部流程的问题，请礼貌引导用户联系客服经理，严禁编造信息。
你的回答应该简洁、友好、专业。"""
}

# =============================================================================
# Mock 数据配置
# =============================================================================

# Mock 用户数据
MOCK_USERS = {
    "admin": {
        "username": "admin",
        "password": "123456",
        "role": "admin",
        "display_name": "系统管理员",
        "created_at": "2024-01-01"
    },
    "manager": {
        "username": "manager",
        "password": "123456",
        "role": "manager",
        "display_name": "客服经理",
        "created_at": "2024-01-01"
    },
    "reception": {
        "username": "reception",
        "password": "123456",
        "role": "reception",
        "display_name": "前台",
        "created_at": "2024-01-01"
    }
}

# Mock 文档数据
MOCK_DOCUMENTS = [
    {
        "id": "doc_001",
        "title": "公司介绍",
        "type": "公开文档",
        "content": "欢迎了解我们公司...",
        "permission_level": 1,
        "created_at": "2024-01-15",
        "updated_at": "2024-03-01"
    },
    {
        "id": "doc_002",
        "title": "营业时间",
        "type": "公开文档",
        "content": "周一至周五 9:00-18:00...",
        "permission_level": 1,
        "created_at": "2024-01-15",
        "updated_at": "2024-02-20"
    },
    {
        "id": "doc_003",
        "title": "基本服务政策",
        "type": "公开文档",
        "content": "我们的服务承诺...",
        "permission_level": 1,
        "created_at": "2024-01-20",
        "updated_at": "2024-03-05"
    },
    {
        "id": "doc_004",
        "title": "客服培训手册",
        "type": "内部资料",
        "content": "客服标准话术...",
        "permission_level": 2,
        "created_at": "2024-02-01",
        "updated_at": "2024-03-10"
    },
    {
        "id": "doc_005",
        "title": "热点投诉案例分析",
        "type": "内部资料",
        "content": "2024年Q1投诉分析...",
        "permission_level": 2,
        "created_at": "2024-02-15",
        "updated_at": "2024-03-08"
    },
    {
        "id": "doc_006",
        "title": "服务流程优化指南",
        "type": "内部资料",
        "content": "如何优化客户接待流程...",
        "permission_level": 2,
        "created_at": "2024-02-20",
        "updated_at": "2024-03-12"
    },
    {
        "id": "doc_007",
        "title": "系统架构文档",
        "type": "敏感资料",
        "content": "系统技术架构详情...",
        "permission_level": 3,
        "created_at": "2024-01-10",
        "updated_at": "2024-03-01"
    },
    {
        "id": "doc_008",
        "title": "数据库配置说明",
        "type": "敏感资料",
        "content": "数据库连接配置...",
        "permission_level": 3,
        "created_at": "2024-01-12",
        "updated_at": "2024-02-28"
    },
    {
        "id": "doc_009",
        "title": "安全策略文档",
        "type": "敏感资料",
        "content": "系统安全策略...",
        "permission_level": 3,
        "created_at": "2024-01-15",
        "updated_at": "2024-03-10"
    },
    {
        "id": "doc_010",
        "title": "审计日志规范",
        "type": "敏感资料",
        "content": "系统审计规范...",
        "permission_level": 3,
        "created_at": "2024-02-01",
        "updated_at": "2024-03-15"
    }
]

# Mock 热知识数据
MOCK_HOT_KNOWLEDGE = [
    {
        "id": "hot_001",
        "title": "春节期间营业时间调整",
        "content": "2024年春节假期调整为...",
        "added_at": "2024-02-01",
        "priority": "high"
    }
]

# =============================================================================
# UI 配置
# =============================================================================

# 应用信息
APP_INFO = {
    "name": "IHG智能问答平台",
    "version": "1.0.0",
    "logo": "🤖",
    "company": "IHG Hotels & Resorts",
    "system_name": "Knowledge Base Q&A System",
}

# 页面配置
PAGE_CONFIG = {
    "login": {
        "title": "Sign In",
        "background_image": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=1920",
    },
    "chat": {
        "title": "智能对话",
        "iframe_height": "80vh",
    },
    "documents": {
        "title": "文档中心",
    },
    "hot_knowledge": {
        "title": "热知识管理",
    }
}

# =============================================================================
# 路径配置
# =============================================================================

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 模板路径
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# 静态文件路径
STATIC_DIR = os.path.join(BASE_DIR, "static")

# 日志路径
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 确保目录存在
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
