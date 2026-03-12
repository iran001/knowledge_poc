"""
IHG智能问答平台 - FastAPI 后端
使用Jinja2模板引擎和配置文件
"""

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn
import httpx
import uuid

# 导入配置文件
from config import (
    SERVER_CONFIG, DIFY_CONFIG,
    ROLE_DISPLAY_MAP, ROLE_LEVEL_MAP, ROLE_PROMPT_MAP,
    MOCK_USERS, MOCK_DOCUMENTS, MOCK_HOT_KNOWLEDGE,
    APP_INFO, PAGE_CONFIG, TEMPLATE_DIR
)

# =============================================================================
# FastAPI 应用实例
# =============================================================================
app = FastAPI(
    title=APP_INFO["name"],
    description="支持RBAC权限控制和动态Prompt注入的AI知识管理后端",
    version=APP_INFO["version"]
)

# =============================================================================
# 模板引擎配置
# =============================================================================
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# =============================================================================
# CORS 配置
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 内存数据存储
# =============================================================================
# 会话存储（生产环境应使用Redis或数据库）
sessions: Dict[str, Dict[str, Any]] = {}

# 热知识数据（可修改）
hot_knowledge_db = MOCK_HOT_KNOWLEDGE.copy()

# =============================================================================
# Pydantic 模型
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    role: str
    message: str
    conversation_id: Optional[str] = None


class DocumentFilterRequest(BaseModel):
    role: str
    search_keyword: Optional[str] = None


class HotKnowledgeRequest(BaseModel):
    title: str
    content: str
    priority: str = "normal"


# =============================================================================
# 工具函数
# =============================================================================

def get_user_role_level(role: str) -> int:
    """获取角色的权限级别"""
    return ROLE_LEVEL_MAP.get(role, 0)


def filter_documents_by_role(role: str, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    """根据用户角色过滤文档列表"""
    user_level = get_user_role_level(role)
    
    filtered = [
        doc for doc in MOCK_DOCUMENTS
        if doc["permission_level"] <= user_level
    ]
    
    if keyword:
        keyword = keyword.lower()
        filtered = [
            doc for doc in filtered
            if keyword in doc["title"].lower() or keyword in doc["content"].lower()
        ]
    
    return filtered


def get_system_prompt_by_role(role: str) -> str:
    """根据角色获取对应的System Prompt"""
    return ROLE_PROMPT_MAP.get(role, ROLE_PROMPT_MAP["reception"])


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """从会话中获取当前用户"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        return sessions[session_id]
    return None


# =============================================================================
# 页面路由 - 使用模板渲染
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 未登录显示登录页，已登录重定向到聊天页"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/page/chat")
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": APP_INFO["name"],
        "logo": APP_INFO["logo"],
        "background_image": PAGE_CONFIG["login"]["background_image"],
        "error": None,
        "warning": None,
        "user": None
    })


@app.get("/page/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """智能对话页面"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "app_name": APP_INFO["name"],
        "logo": APP_INFO["logo"],
        "page_title": PAGE_CONFIG["chat"]["title"],
        "dify_chatbot_url": DIFY_CONFIG["chatbot_url"],
        "user": user,
        "active_page": "chat"
    })


@app.get("/page/documents", response_class=HTMLResponse)
async def documents_page(request: Request, keyword: str = ""):
    """文档中心页面"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")
    
    documents = filter_documents_by_role(user["role"], keyword)
    
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "app_name": APP_INFO["name"],
        "logo": APP_INFO["logo"],
        "page_title": PAGE_CONFIG["documents"]["title"],
        "user": user,
        "active_page": "documents",
        "documents": documents,
        "total_count": len(documents),
        "visible_permission": f"级别 {get_user_role_level(user['role'])} 及以下",
        "keyword": keyword
    })


@app.get("/page/hot-knowledge", response_class=HTMLResponse)
async def hot_knowledge_page(request: Request):
    """热知识管理页面"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")
    
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    return templates.TemplateResponse("hot_knowledge.html", {
        "request": request,
        "app_name": APP_INFO["name"],
        "logo": APP_INFO["logo"],
        "page_title": PAGE_CONFIG["hot_knowledge"]["title"],
        "user": user,
        "active_page": "hot_knowledge",
        "knowledge_list": hot_knowledge_db
    })


# =============================================================================
# API 路由
# =============================================================================

@app.post("/api/login")
async def api_login(request: Request, login_data: LoginRequest):
    """API登录接口"""
    user = MOCK_USERS.get(login_data.username)
    
    if not user or user["password"] != login_data.password:
        return {"success": False, "message": "用户名或密码错误"}
    
    # 创建会话
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"]
    }
    
    response = {"success": True, "message": "登录成功", "user": {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"]
    }}
    
    # 设置Cookie
    resp = JSONResponse(content=response)
    resp.set_cookie(key="session_id", value=session_id, httponly=True)
    return resp


@app.post("/api/login-form")
async def api_login_form(request: Request, username: str = Form(...), password: str = Form(...)):
    """表单登录接口"""
    user = MOCK_USERS.get(username)
    
    if not user or user["password"] != password:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": APP_INFO["name"],
            "logo": APP_INFO["logo"],
            "background_image": PAGE_CONFIG["login"]["background_image"],
            "error": "用户名或密码错误",
            "warning": None,
            "user": None
        })
    
    # 创建会话
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"]
    }
    
    response = RedirectResponse(url="/page/chat", status_code=302)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response


@app.post("/api/logout")
async def api_logout(request: Request):
    """登出接口"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_id")
    return response


@app.post("/api/chat")
async def api_chat(request: Request, chat_data: ChatRequest):
    """聊天接口 - 代理转发到 Dify"""
    try:
        system_prompt = get_system_prompt_by_role(chat_data.role)
        
        dify_payload = {
            "inputs": {"sys_prompt": system_prompt},
            "query": chat_data.message,
            "response_mode": "blocking",
            "conversation_id": chat_data.conversation_id or "",
            "user": f"user_{chat_data.role}",
            "files": []
        }
        
        async with httpx.AsyncClient(timeout=DIFY_CONFIG["timeout"]) as client:
            response = await client.post(
                f"{DIFY_CONFIG['base_url']}/chat-messages",
                json=dify_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                dify_response = response.json()
                return {
                    "success": True,
                    "role": chat_data.role,
                    "system_prompt_injected": True,
                    "dify_response": dify_response
                }
            else:
                # Mock响应
                return {
                    "success": True,
                    "role": chat_data.role,
                    "system_prompt_injected": True,
                    "mock_mode": True,
                    "answer": f"【角色: {chat_data.role}】\n\n已注入对应角色的System Prompt。\n\n用户问题: {chat_data.message}"
                }
                
    except Exception as e:
        return {
            "success": True,
            "role": chat_data.role,
            "system_prompt_injected": True,
            "mock_mode": True,
            "answer": f"【角色: {chat_data.role}】\n\n您说: {chat_data.message}\n\n(当前为模拟模式)"
        }


@app.post("/api/documents")
async def api_documents(request: Request, filter_data: DocumentFilterRequest):
    """获取文档列表接口"""
    documents = filter_documents_by_role(filter_data.role, filter_data.search_keyword)
    
    return {
        "success": True,
        "role": filter_data.role,
        "role_display": ROLE_DISPLAY_MAP.get(filter_data.role, {}).get("name", "未知"),
        "total_count": len(documents),
        "visible_permission": f"级别 {get_user_role_level(filter_data.role)} 及以下",
        "documents": documents
    }


@app.get("/api/hot-knowledge")
async def api_get_hot_knowledge(request: Request):
    """获取热知识列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    return {
        "success": True,
        "knowledge": hot_knowledge_db
    }


@app.post("/api/hot-knowledge")
async def api_add_hot_knowledge(request: Request, data: HotKnowledgeRequest):
    """添加热知识API接口（仅管理员）"""
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    new_knowledge = {
        "id": f"hot_{len(hot_knowledge_db) + 1:03d}",
        "title": data.title,
        "content": data.content,
        "priority": data.priority,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    hot_knowledge_db.append(new_knowledge)
    
    return {
        "success": True,
        "message": "热知识添加成功",
        "knowledge": new_knowledge
    }


@app.post("/api/hot-knowledge-form")
async def api_add_hot_knowledge_form(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    priority: str = Form("normal")
):
    """添加热知识表单接口（仅管理员）"""
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    new_knowledge = {
        "id": f"hot_{len(hot_knowledge_db) + 1:03d}",
        "title": title,
        "content": content,
        "priority": priority,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    hot_knowledge_db.append(new_knowledge)
    
    return RedirectResponse(url="/page/hot-knowledge", status_code=302)


# =============================================================================
# 启动入口
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"{APP_INFO['name']} - FastAPI 服务")
    print("=" * 60)
    print("服务地址:")
    print(f"  • 首页:      http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['backend_port']}/")
    print(f"  • API文档:   http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['backend_port']}/docs")
    print(f"  • ReDoc:     http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['backend_port']}/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "backend:app",
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["backend_port"],
        reload=SERVER_CONFIG["reload"]
    )
