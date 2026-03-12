"""
AI知识管理平台 - FastAPI 统一服务
集成后端API和前端代理
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import uvicorn
from datetime import datetime
import httpx
import json
import subprocess
import time
import os

# =============================================================================
# FastAPI 应用实例
# =============================================================================
app = FastAPI(
    title="AI知识管理平台",
    description="集成前后端的AI知识管理平台",
    version="1.0.0"
)

# =============================================================================
# CORS 配置 - 允许前端跨域访问
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Mock 数据存储（内存中，生产环境应使用数据库）
# =============================================================================

# 角色类型定义
RoleType = Literal["admin", "manager", "reception"]

# 用户数据表 - Mock登录数据
USERS_DB: Dict[str, Dict[str, Any]] = {
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

# 【核心】角色-System Prompt 映射表
# 这是实现"基于角色的AI回答控制"的关键配置
# 当用户发起对话时，后端根据用户角色从此表读取对应的Prompt，注入到Dify请求中
ROLE_PROMPT_MAP: Dict[RoleType, str] = {
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

# 角色权限级别映射（数值越大权限越高）
ROLE_LEVEL_MAP: Dict[RoleType, int] = {
    "reception": 1,   # 前台 - 基础权限
    "manager": 2,     # 客服经理 - 中等权限
    "admin": 3        # 系统管理员 - 最高权限
}

# Mock 文档数据表 - 每个文档有权限等级要求
DOCUMENTS_DB: List[Dict[str, Any]] = [
    {
        "id": "doc_001",
        "title": "公司介绍",
        "type": "公开文档",
        "content": "欢迎了解我们公司...",
        "permission_level": 1,  # 前台及以上可查看
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
        "permission_level": 2,  # 经理及以上可查看
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
        "permission_level": 3,  # 仅管理员可查看
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

# 热知识缓存（模拟实时更新的知识）
HOT_KNOWLEDGE_DB: List[Dict[str, Any]] = [
    {
        "id": "hot_001",
        "title": "春节期间营业时间调整",
        "content": "2024年春节假期调整为...",
        "added_at": "2024-02-01",
        "priority": "high"
    }
]

# =============================================================================
# Pydantic 模型定义 - 请求/响应数据结构
# =============================================================================

class LoginRequest(BaseModel):
    """登录请求体"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应体"""
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """聊天请求体"""
    role: RoleType  # 用户角色，用于获取对应的System Prompt
    message: str    # 用户输入的消息
    conversation_id: Optional[str] = None  # 对话ID，用于上下文保持


class DocumentFilterRequest(BaseModel):
    """文档列表请求体"""
    role: RoleType  # 用户角色，用于过滤文档
    search_keyword: Optional[str] = None  # 可选的搜索关键词


class HotKnowledgeRequest(BaseModel):
    """热知识上传请求体（仅管理员可用）"""
    title: str
    content: str
    priority: str = "normal"


# =============================================================================
# 工具函数
# =============================================================================

def get_user_role_level(role: RoleType) -> int:
    """获取角色的权限级别"""
    return ROLE_LEVEL_MAP.get(role, 0)


def filter_documents_by_role(role: RoleType, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    根据用户角色过滤文档列表
    这是实现"基于角色的文档访问控制"的核心函数
    """
    user_level = get_user_role_level(role)

    # 只返回权限级别 <= 用户级别的文档
    filtered = [
        doc for doc in DOCUMENTS_DB
        if doc["permission_level"] <= user_level
    ]

    # 如果有搜索关键词，进一步过滤
    if keyword:
        keyword = keyword.lower()
        filtered = [
            doc for doc in filtered
            if keyword in doc["title"].lower() or keyword in doc["content"].lower()
        ]

    return filtered


def get_system_prompt_by_role(role: RoleType) -> str:
    """
    根据角色获取对应的System Prompt
    【核心逻辑】这是实现"角色Prompt注入"的关键
    """
    return ROLE_PROMPT_MAP.get(role, ROLE_PROMPT_MAP["reception"])


# =============================================================================
# API 路由定义
# =============================================================================

@app.get("/")
async def root():
    """根路由 - API健康检查"""
    return {
        "status": "running",
        "service": "AI知识管理平台 API",
        "version": "1.0.0"
    }


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录接口
    验证用户名密码，返回用户信息和角色
    """
    user = USERS_DB.get(request.username)

    if not user or user["password"] != request.password:
        return LoginResponse(
            success=False,
            message="用户名或密码错误"
        )

    # 返回用户信息（去除敏感字段如密码）
    user_info = {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
        "created_at": user["created_at"]
    }

    return LoginResponse(
        success=True,
        message="登录成功",
        user=user_info
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    聊天接口 - 代理转发到 Dify
    【核心逻辑】根据用户角色动态注入 System Prompt
    """
    try:
        # 1. 获取当前角色对应的 System Prompt
        system_prompt = get_system_prompt_by_role(request.role)

        # 2. 构建 Dify API 请求体
        # 注意：以下结构为示例，实际需根据 Dify API 文档调整
        dify_payload = {
            "inputs": {
                # 将角色的 System Prompt 作为系统变量传入
                # Dify 中可以在应用编排时使用 {{#sys_prompt#}} 引用
                "sys_prompt": system_prompt
            },
            "query": request.message,
            "response_mode": "blocking",  # 或 "streaming" 用于流式响应
            "conversation_id": request.conversation_id or "",
            "user": f"user_{request.role}",  # 用户标识
            "files": []
        }

        # 3. 调用 Dify API
        # Dify API 端点：http://116.62.30.61/v1
        # 注意：此处需要根据 Dify 实际认证方式添加 API Key
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://116.62.30.61/v1/chat-messages",  # 根据实际API路径调整
                json=dify_payload,
                headers={
                    "Content-Type": "application/json",
                    # "Authorization": "Bearer YOUR_DIFY_API_KEY"  # 如需认证，取消注释
                }
            )

            if response.status_code == 200:
                dify_response = response.json()
                return {
                    "success": True,
                    "role": request.role,
                    "system_prompt_injected": True,  # 标识Prompt已成功注入
                    "dify_response": dify_response
                }
            else:
                # 如果 Dify 服务不可用，返回模拟响应（演示用）
                return {
                    "success": True,
                    "role": request.role,
                    "system_prompt_injected": True,
                    "mock_mode": True,
                    "answer": f"【角色: {request.role}】\n\n已注入对应角色的System Prompt，实际应返回Dify的回复。\n\n用户问题: {request.message}\n\n使用的Prompt: {system_prompt[:50]}..."
                }

    except Exception as e:
        # 异常时返回模拟响应，确保前端可用
        return {
            "success": True,
            "role": request.role,
            "system_prompt_injected": True,
            "mock_mode": True,
            "answer": f"【角色: {request.role}】\n\n您说: {request.message}\n\n(当前为模拟模式，实际生产环境将调用Dify API)"
        }


@app.post("/api/documents")
async def get_documents(request: DocumentFilterRequest):
    """
    获取文档列表接口
    【权限控制】根据用户角色返回不同可见范围的文档
    """
    documents = filter_documents_by_role(request.role, request.search_keyword)

    # 根据角色添加额外的元数据
    role_names = {
        "admin": "系统管理员",
        "manager": "客服经理",
        "reception": "前台"
    }

    return {
        "success": True,
        "role": request.role,
        "role_display": role_names.get(request.role, "未知"),
        "total_count": len(documents),
        "visible_permission": f"级别 {get_user_role_level(request.role)} 及以下",
        "documents": documents
    }


@app.get("/api/documents/{doc_id}")
async def get_document_detail(doc_id: str, role: RoleType):
    """
    获取单个文档详情
    【权限控制】检查用户是否有权限查看该文档
    """
    user_level = get_user_role_level(role)

    # 查找文档
    doc = next((d for d in DOCUMENTS_DB if d["id"] == doc_id), None)

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限检查
    if doc["permission_level"] > user_level:
        raise HTTPException(
            status_code=403,
            detail="权限不足，无法查看此文档"
        )

    return {
        "success": True,
        "document": doc
    }


@app.get("/api/hot-knowledge")
async def get_hot_knowledge(role: RoleType):
    """
    获取热知识列表
    所有登录用户均可查看
    """
    return {
        "success": True,
        "knowledge": HOT_KNOWLEDGE_DB
    }


@app.post("/api/hot-knowledge")
async def add_hot_knowledge(request: HotKnowledgeRequest, role: RoleType):
    """
    添加热知识（仅管理员可用）
    【权限控制】演示管理员专属功能
    """
    # 权限检查 - 仅管理员可添加
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="权限不足，仅系统管理员可添加热知识"
        )

    new_knowledge = {
        "id": f"hot_{len(HOT_KNOWLEDGE_DB) + 1:03d}",
        "title": request.title,
        "content": request.content,
        "priority": request.priority,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    }

    HOT_KNOWLEDGE_DB.append(new_knowledge)

    return {
        "success": True,
        "message": "热知识添加成功",
        "knowledge": new_knowledge
    }


@app.get("/api/ragflow/documents")
async def get_ragflow_documents(role: RoleType, keyword: Optional[str] = None):
    """
    代理 RagFlow 文档列表接口
    【说明】此接口演示如何代理转发到 RagFlow
    实际使用时根据 RagFlow API 文档调整
    """
    # 注意：RagFlow API 端点：http://118.31.184.47/user-setting/api
    # 以下代码为示例结构

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 根据实际RagFlow API调整
            response = await client.get(
                "http://118.31.184.47/user-setting/api/documents",
                params={"keyword": keyword} if keyword else {},
                headers={
                    # "Authorization": "Bearer YOUR_RAGFLOW_API_KEY"
                }
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "source": "ragflow",
                    "data": response.json()
                }
            else:
                # 返回Mock数据作为回退
                raise Exception("RagFlow服务暂时不可用")

    except Exception as e:
        # 如果RagFlow不可用，返回Mock文档（根据角色过滤）
        mock_docs = filter_documents_by_role(role, keyword)
        return {
            "success": True,
            "source": "mock",
            "role": role,
            "note": "当前返回Mock数据，生产环境将连接RagFlow",
            "documents": mock_docs
        }


# =============================================================================
# 前端路由 - 提供统一入口
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    根路由 - 返回集成前端页面
    使用 iframe 嵌入 Streamlit 前端
    """
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI知识管理平台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 1.5rem;
            font-weight: 500;
        }
        .header-links a {
            color: white;
            text-decoration: none;
            margin-left: 1.5rem;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        .header-links a:hover {
            opacity: 1;
            text-decoration: underline;
        }
        .container {
            display: flex;
            height: calc(100vh - 60px);
        }
        .sidebar {
            width: 200px;
            background: white;
            border-right: 1px solid #e0e0e0;
            padding: 1rem;
        }
        .nav-item {
            display: block;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 8px;
            text-decoration: none;
            color: #333;
            transition: all 0.3s;
        }
        .nav-item:hover, .nav-item.active {
            background: #f0f0f0;
            color: #667eea;
        }
        .nav-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .main-content {
            flex: 1;
            position: relative;
        }
        .iframe-container {
            width: 100%;
            height: 100%;
            border: none;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI知识管理平台</h1>
        <div class="header-links">
            <a href="/docs" target="_blank">API文档</a>
            <a href="/redoc" target="_blank">ReDoc</a>
        </div>
    </div>
    <div class="container">
        <div class="main-content">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在加载前端界面...</p>
                <p style="font-size: 0.85rem; margin-top: 0.5rem; color: #999;">
                    如果长时间未加载，请<a href="http://localhost:8501" style="color: #667eea;">直接访问</a>
                </p>
            </div>
            <iframe 
                id="frontend-frame"
                class="iframe-container" 
                src="http://localhost:8501"
                style="display: none;"
                onload="document.getElementById('loading').style.display='none'; this.style.display='block';">
            </iframe>
        </div>
    </div>
    <script>
        // 自动检测前端是否可用
        setTimeout(() => {
            const frame = document.getElementById('frontend-frame');
            frame.style.display = 'block';
        }, 2000);
    </script>
</body>
</html>
    """)


# =============================================================================
# 启动入口 - 同时启动 FastAPI 和 Streamlit
# =============================================================================

def start_streamlit():
    """在后台启动 Streamlit"""
    import subprocess
    import sys
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(current_dir, "frontend.py")
    
    # 启动 Streamlit，输出到日志文件
    cmd = [
        sys.executable, "-m", "streamlit", "run", frontend_path,
        "--server.port", "8501",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    log_file = open("streamlit.log", "w")
    return subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)


if __name__ == "__main__":
    print("=" * 60)
    print("AI知识管理平台 - 统一服务")
    print("=" * 60)
    print("正在启动服务...")
    print("-" * 60)
    
    # 启动 Streamlit 前端
    print("[1/2] 正在启动 Streamlit 前端服务...")
    streamlit_process = start_streamlit()
    time.sleep(3)  # 等待 Streamlit 启动
    print("      Streamlit 前端已启动: http://localhost:8501")
    
    # 启动 FastAPI
    print("[2/2] 正在启动 FastAPI 后端服务...")
    print("-" * 60)
    print("访问地址:")
    print("  • 统一入口:    http://localhost:8000")
    print("  • 前端直访:    http://localhost:8501")
    print("  • API文档:     http://localhost:8000/docs")
    print("  • ReDoc文档:   http://localhost:8000/redoc")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "backend:app",
            host="0.0.0.0",
            port=8000,
            reload=False
        )
    finally:
        # 关闭 Streamlit 进程
        if streamlit_process:
            streamlit_process.terminate()
            print("\nStreamlit 服务已关闭")
