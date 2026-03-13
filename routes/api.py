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
import json

from config import (
    SERVER_CONFIG, DIFY_CONFIG,
    ROLE_DISPLAY_MAP, ROLE_LEVEL_MAP, ROLE_PROMPT_MAP,
    MOCK_USERS, APP_INFO, PAGE_CONFIG, TEMPLATE_DIR,
    RAGFLOW_CONFIG
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


async def fetch_documents_from_api(
    role: str,
    keyword: str = "",
    page: int = 1,
    page_size: int = 10
) -> Dict[str, Any]:
    """
    从 RAGFlow API 获取文档列表
    """
    print("\n" + "=" * 80)
    print("[RAGFlow API] fetch_documents_from_api begin")
    print(f"[RAGFlow API] Input params: role={role}, keyword={keyword}, page={page}, page_size={page_size}")
    
    try:
        base_url = RAGFLOW_CONFIG["base_url"]
        dataset_id = RAGFLOW_CONFIG["dataset_id"]
        api_key = RAGFLOW_CONFIG["api_key"]
        
        print(f"[RAGFlow API] RAGFLOW_CONFIG: base_url={base_url}, dataset_id={dataset_id}")
       
        
        # 构建请求 URL
        url = f"{base_url}/datasets/{dataset_id}/documents"

        params = {
            "page": page,
            "page_size": page_size,
            "orderby": "create_time",
            "desc": "true",
            "keywords": keyword
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # 记录请求参数
        print("[RAGFlow API Request]")
        print(f"  URL: {url}")
        print(f"  Method: GET")
        print(f"  Headers: Authorization=Bearer {api_key[:10]}...")
        print(f"  Params:")
        for k, v in params.items():
            print(f"    {k}: {v}")
        print("-" * 80)
        
        async with httpx.AsyncClient(timeout=float(RAGFLOW_CONFIG.get("timeout", 30))) as client:
            response = await client.get(url, params=params, headers=headers)
            
            # 记录响应状态
            print("[RAGFlow API Response]")
            print(f"  Status Code: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code != 200:
                print(f"[RAGFlow API] Error: {response.status_code}")
                print(f"[RAGFlow API] Response Text: {response.text[:500]}")
                return {"documents": [], "total": 0}
            
            data = response.json()
            
            # 记录完整响应数据
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
            print(f"  Response Body: {data_str}")
            print("-" * 80)
            
            if data.get("code") == 0:
                docs_data = data.get("data", {})
                docs = docs_data.get("docs", [])
                total = docs_data.get("total", 0)  # API返回的是 total
                
                print(f"[RAGFlow API] Success: Fetched {len(docs)} documents, total: {total}")
                
                documents = []
                for doc in docs:
                    documents.append({
                        "id": doc.get("id", ""),
                        "title": doc.get("name", "未命名文档"),
                        "content": doc.get("content", "") or doc.get("description", "暂无描述"),
                        "type": doc.get("type", "未知"),
                        "updated_at": doc.get("update_time", doc.get("create_time", "未知")),
                        "permission_level": {"admin": 3, "manager": 2, "reception": 1}.get(role, 1),
                        "chunk_count": doc.get("chunk_count", 0),
                        "token_count": doc.get("token_count", 0),
                        "progress": doc.get("progress", 0),
                        "progress_msg": doc.get("progress_msg", ""),
                        "run": doc.get("run", ""),
                        "status": doc.get("status", "")
                    })
                
                return {"documents": documents, "total": total}
            else:
                print(f"[RAGFlow API] API Error Code: {data.get('code')}, Message: {data.get('message', 'Unknown error')}")
                return {"documents": [], "total": 0}
                
    except Exception as e:
        print(f"[RAGFlow API] Exception: {e}")
        import traceback
        traceback.print_exc()
        return {"documents": [], "total": 0}
    finally:
        print("=" * 80 + "\n")


@router.get("/documents")
async def api_get_documents(
    request: Request,
    keyword: str = "",
    page: int = 1,
    page_size: int = 10
):
    """获取文档列表接口 (GET) - 供前端 AJAX 调用"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    result = await fetch_documents_from_api(
        role=user["role"],
        keyword=keyword,
        page=page,
        page_size=page_size
    )
    
    return {
        "success": True,
        "role": user["role"],
        "role_display": ROLE_DISPLAY_MAP.get(user["role"], {}).get("name", "未知"),
        "total_count": result["total"],
        "current_page": page,
        "total_pages": (result["total"] + page_size - 1) // page_size if result["total"] > 0 else 1,
        "page_size": page_size,
        "visible_permission": ROLE_DISPLAY_MAP.get(user["role"], {}).get("name", "未知"),
        "documents": result["documents"]
    }


@router.get("/hot-knowledge")
async def api_get_hot_knowledge(request: Request):
    """获取文件列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    return {
        "success": True,
        "knowledge": hot_knowledge_db
    }


@router.post("/hot-knowledge")
async def api_add_hot_knowledge(request: Request, data: HotKnowledgeRequest):
    """添加文件API接口（仅管理员）"""
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
        "message": "文件添加成功",
        "knowledge": new_knowledge
    }


@router.post("/hot-knowledge-form")
async def api_add_hot_knowledge_form(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    priority: str = Form("normal")
):
    """添加文件表单接口（仅管理员）"""
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
