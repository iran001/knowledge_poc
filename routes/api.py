"""
API路由 - RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import httpx

from config import (
    SERVER_CONFIG, DIFY_CONFIG,
    ROLE_DISPLAY_MAP, ROLE_LEVEL_MAP, ROLE_PROMPT_MAP,
    MOCK_USERS, APP_INFO, PAGE_CONFIG, TEMPLATE_DIR
)
from fastapi.templating import Jinja2Templates
from data_store import sessions, hot_knowledge_db
from chat_history import save_chat_message, load_chat_history, get_user_conversations, delete_chat_history

# 创建路由器和模板
router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


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


class SaveMessageRequest(BaseModel):
    conversation_id: str
    role: str
    content: str
    think_content: str = ""


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    history: List[Dict[str, Any]]


# =============================================================================
# 工具函数
# =============================================================================

def get_user_role_level(role: str) -> int:
    """获取角色的权限级别"""
    return ROLE_LEVEL_MAP.get(role, 0)


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
# API 路由
# =============================================================================

@router.post("/login")
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


@router.post("/login-form")
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


@router.post("/logout")
async def api_logout(request: Request):
    """登出接口"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_id")
    return response


@router.post("/chat")
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


@router.post("/documents")
async def api_documents(request: Request, filter_data: DocumentFilterRequest):
    """获取文档列表接口"""
    from config import MOCK_DOCUMENTS
    user_level = get_user_role_level(filter_data.role)
    
    documents = [
        doc for doc in MOCK_DOCUMENTS
        if doc["permission_level"] <= user_level
    ]
    
    if filter_data.search_keyword:
        keyword = filter_data.search_keyword.lower()
        documents = [
            doc for doc in documents
            if keyword in doc["title"].lower() or keyword in doc["content"].lower()
        ]
    
    return {
        "success": True,
        "role": filter_data.role,
        "role_display": ROLE_DISPLAY_MAP.get(filter_data.role, {}).get("name", "未知"),
        "total_count": len(documents),
        "visible_permission": f"级别 {user_level} 及以下",
        "documents": documents
    }


@router.get("/hot-knowledge")
async def api_get_hot_knowledge(request: Request):
    """获取热知识列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    return {
        "success": True,
        "knowledge": hot_knowledge_db
    }


@router.post("/hot-knowledge")
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


@router.post("/hot-knowledge-form")
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
# 对话历史 API
# =============================================================================

@router.post("/chat-history/save")
async def api_save_chat_message(request: Request, data: SaveMessageRequest):
    """保存对话消息"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    metadata = {
        "user_id": user.get("username"),
        "user_role": user.get("role"),
        "user_display_name": user.get("display_name")
    }
    
    success = save_chat_message(
        conversation_id=data.conversation_id,
        role=data.role,
        content=data.content,
        think_content=data.think_content,
        metadata=metadata
    )
    
    return {
        "success": success,
        "conversation_id": data.conversation_id
    }


@router.get("/chat-history/{conversation_id}")
async def api_get_chat_history(request: Request, conversation_id: str):
    """获取对话历史"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    history = load_chat_history(conversation_id)
    
    # 过滤出当前用户的消息
    user_history = [
        msg for msg in history 
        if msg.get("metadata", {}).get("user_id") == user.get("username")
    ]
    
    return {
        "success": True,
        "conversation_id": conversation_id,
        "history": user_history
    }


@router.get("/chat-history")
async def api_get_user_conversations(request: Request):
    """获取用户的所有会话列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    conversations = get_user_conversations(user.get("username"))
    
    return {
        "success": True,
        "conversations": conversations
    }


@router.delete("/chat-history/{conversation_id}")
async def api_delete_chat_history(request: Request, conversation_id: str):
    """删除对话历史"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    # 检查是否是该用户的对话
    history = load_chat_history(conversation_id)
    user_messages = [m for m in history if m.get("metadata", {}).get("user_id") == user.get("username")]
    
    if not user_messages:
        raise HTTPException(status_code=403, detail="无权删除此对话")
    
    success = delete_chat_history(conversation_id)
    
    return {
        "success": success,
        "conversation_id": conversation_id
    }
