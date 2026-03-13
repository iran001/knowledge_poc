"""
页面路由 - 使用Jinja2模板渲染的页面
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any

from config import (
    APP_INFO, PAGE_CONFIG, TEMPLATE_DIR, MOCK_DOCUMENTS,
    ROLE_LEVEL_MAP, ROLE_PROMPT_MAP, DIFY_CONFIG,
    DIFY_ROLE_INPUTS_MAP
)
from data_store import sessions, hot_knowledge_db
import json

# 创建路由器和模板
router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def get_user_role_level(role: str) -> int:
    """获取角色的权限级别"""
    return ROLE_LEVEL_MAP.get(role, 0)


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """从会话中获取当前用户"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        return sessions[session_id]
    return None


def filter_documents_by_role(role: str, keyword: Optional[str] = None):
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


def filter_documents_by_role(role: str, keyword: Optional[str] = None):
    """根据用户角色过滤文档列表"""
    from config import MOCK_DOCUMENTS
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


@router.get("/", response_class=HTMLResponse)
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


@router.get("/page/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """智能对话页面"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")

    # 获取用户角色相关的 Dify 配置
    user_role = user.get("role", "reception")
    display_name = user.get("display_name", "访客")

    # 根据角色获取系统提示词和输入变量
    system_prompt = ROLE_PROMPT_MAP.get(user_role, ROLE_PROMPT_MAP["reception"])
    role_inputs = DIFY_ROLE_INPUTS_MAP.get(user_role, DIFY_ROLE_INPUTS_MAP["reception"])

    # 打印配置信息到控制台
    print("=" * 60)
    print(f"[Dify Chatbot Config] User: {display_name} (Role: {user_role})")
    print(f"[Dify Chatbot Config] system_prompt: {system_prompt}")
    print(f"[Dify Chatbot Config] role_inputs: {json.dumps(role_inputs, ensure_ascii=False)}")
    print("=" * 60)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "app_name": APP_INFO["name"],
        "logo": APP_INFO["logo"],
        "page_title": PAGE_CONFIG["chat"]["title"],
        "user": user,
        "active_page": "chat",
        # Dify API 配置
        "dify_config": DIFY_CONFIG,
        "role_inputs": json.dumps(role_inputs, ensure_ascii=False),
        "system_prompt": system_prompt,
        "user_role": user_role
    })


@router.get("/page/documents", response_class=HTMLResponse)
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


@router.get("/page/hot-knowledge", response_class=HTMLResponse)
async def hot_knowledge_page(request: Request):
    """热知识管理页面"""
    from fastapi import HTTPException
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
