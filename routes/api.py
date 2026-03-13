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
from data_store import sessions, knowledge_upload_db
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


class KnowledgeUploadRequest(BaseModel):
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


async def _fetch_single_dataset(
    client: httpx.AsyncClient,
    base_url: str,
    dataset_id: str,
    api_key: str,
    keyword: str,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """
    从单个 RAGFlow dataset 获取文档列表
    返回: {"documents": [...], "total": int}
    """
    url = f"{base_url}/datasets/{dataset_id}/documents"
    params = {
        "page": page,
        "page_size": page_size,
        "orderby": "create_time",
        "desc": "true",
        "keywords": keyword
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"[RAGFlow API] Fetching from dataset: {dataset_id}")
    print(f"[RAGFlow API]   URL: {url}")
    print(f"[RAGFlow API]   Params: {params}")
    
    response = await client.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        print(f"[RAGFlow API] Error from dataset {dataset_id}: {response.status_code}")
        return {"documents": [], "total": 0}
    
    data = response.json()
    
    if data.get("code") != 0:
        print(f"[RAGFlow API] API Error from dataset {dataset_id}: {data.get('code')}")
        return {"documents": [], "total": 0}
    
    docs_data = data.get("data", {})
    docs = docs_data.get("docs", [])
    total = docs_data.get("total", 0)
    
    documents = []
    for doc in docs:
        documents.append({
            "id": doc.get("id", ""),
            "title": doc.get("name", "未命名文档"),
            "content": doc.get("content", "") or doc.get("description", "暂无描述"),
            "type": doc.get("type", "未知"),
            "updated_at": doc.get("update_time", doc.get("create_time", "未知")),
            "chunk_count": doc.get("chunk_count", 0),
            "token_count": doc.get("token_count", 0),
            "progress": doc.get("progress", 0),
            "progress_msg": doc.get("progress_msg", ""),
            "run": doc.get("run", ""),
            "status": doc.get("status", "")
        })
    
    print(f"[RAGFlow API]   Dataset {dataset_id}: {len(documents)} docs, total: {total}")
    return {"documents": documents, "total": total}


async def _fetch_all_documents_from_dataset(
    client: httpx.AsyncClient,
    base_url: str,
    dataset_id: str,
    api_key: str,
    keyword: str
) -> List[Dict[str, Any]]:
    """
    从单个 dataset 获取所有文档（处理分页获取全部）
    """
    all_docs = []
    page = 1
    page_size = 100  # 每次获取较多数据以减少请求次数
    
    while True:
        result = await _fetch_single_dataset(
            client, base_url, dataset_id, api_key, keyword, page, page_size
        )
        
        docs = result.get("documents", [])
        if not docs:
            break
            
        all_docs.extend(docs)
        
        # 如果返回的数据少于 page_size，说明已经获取完毕
        if len(docs) < page_size:
            break
            
        page += 1
        
        # 安全限制：最多获取 1000 条
        if len(all_docs) >= 1000:
            print(f"[RAGFlow API] Reached maximum limit (1000) for dataset {dataset_id}")
            break
    
    return all_docs


async def fetch_documents_from_api(
    role: str,
    keyword: str = "",
    page: int = 1,
    page_size: int = 10
) -> Dict[str, Any]:
    """
    从 RAGFlow API 获取文档列表
    - admin/manager 角色：从 dataset_id、vl_dataset_id、special_dataset_id 三个 dataset 查询并合并
    - reception 角色：从 dataset_id、special_dataset_id 两个 dataset 查询并合并
    """
    print("\n" + "=" * 80)
    print("[RAGFlow API] fetch_documents_from_api begin")
    print(f"[RAGFlow API] Input params: role={role}, keyword={keyword}, page={page}, page_size={page_size}")
    
    try:
        base_url = str(RAGFLOW_CONFIG["base_url"])
        dataset_id = str(RAGFLOW_CONFIG["dataset_id"])
        vl_dataset_id = str(RAGFLOW_CONFIG.get("vl_dataset_id", ""))
        special_dataset_id = str(RAGFLOW_CONFIG.get("special_dataset_id", ""))
        api_key = str(RAGFLOW_CONFIG["api_key"])
        
        print(f"[RAGFlow API] RAGFLOW_CONFIG: base_url={base_url}, dataset_id={dataset_id}, vl_dataset_id={vl_dataset_id}, special_dataset_id={special_dataset_id}")
        
        async with httpx.AsyncClient(timeout=float(RAGFLOW_CONFIG.get("timeout", 60))) as client:
            
            if role == "reception":
                # reception 角色：从 dataset_id 和 special_dataset_id 获取数据
                print(f"[RAGFlow API] Role is 'reception', fetching from dataset_id and special_dataset_id")
                
                docs_from_primary = await _fetch_all_documents_from_dataset(
                    client, base_url, dataset_id, api_key, keyword
                )
                docs_from_special = await _fetch_all_documents_from_dataset(
                    client, base_url, special_dataset_id, api_key, keyword
                )
                
                print(f"[RAGFlow API] Primary dataset: {len(docs_from_primary)} docs")
                print(f"[RAGFlow API] Special dataset: {len(docs_from_special)} docs")
                
                # 合并数据（按 id 去重）
                all_documents = {}
                
                for doc in docs_from_primary:
                    doc["permission_level"] = 1
                    all_documents[doc["id"]] = doc
                
                for doc in docs_from_special:
                    doc["permission_level"] = 1
                    if doc["id"] not in all_documents:
                        all_documents[doc["id"]] = doc
                
                # 排序和分页
                merged_docs = list(all_documents.values())
                merged_docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                merged_total = len(merged_docs)
                
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_docs = merged_docs[start_idx:end_idx]
                
                print(f"[RAGFlow API] Merged: {len(merged_docs)} unique documents")
                print(f"[RAGFlow API] Paginated: page {page}, showing {len(paginated_docs)} of {merged_total} docs")
                print("=" * 80 + "\n")
                
                return {
                    "documents": paginated_docs,
                    "total": merged_total
                }
            
            else:
                # admin/manager 角色：从三个 dataset 获取所有数据后合并
                print(f"[RAGFlow API] Role is '{role}', fetching from all three datasets")
                
                docs_from_primary = await _fetch_all_documents_from_dataset(
                    client, base_url, dataset_id, api_key, keyword
                )
                docs_from_vl = await _fetch_all_documents_from_dataset(
                    client, base_url, vl_dataset_id, api_key, keyword
                )
                docs_from_special = await _fetch_all_documents_from_dataset(
                    client, base_url, special_dataset_id, api_key, keyword
                )
                
                print(f"[RAGFlow API] Primary dataset: {len(docs_from_primary)} docs")
                print(f"[RAGFlow API] VL dataset: {len(docs_from_vl)} docs")
                print(f"[RAGFlow API] Special dataset: {len(docs_from_special)} docs")
                
                # 合并数据（按 id 去重）
                all_documents = {}
                
                for doc in docs_from_primary:
                    doc["permission_level"] = {"admin": 3, "manager": 2}.get(role, 2)
                    all_documents[doc["id"]] = doc
                
                for doc in docs_from_vl:
                    doc["permission_level"] = {"admin": 3, "manager": 2}.get(role, 2)
                    if doc["id"] not in all_documents:
                        all_documents[doc["id"]] = doc
                
                for doc in docs_from_special:
                    doc["permission_level"] = {"admin": 3, "manager": 2}.get(role, 2)
                    if doc["id"] not in all_documents:
                        all_documents[doc["id"]] = doc
                
                # 排序和分页
                merged_docs = list(all_documents.values())
                merged_docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                merged_total = len(merged_docs)
                
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_docs = merged_docs[start_idx:end_idx]
                
                print(f"[RAGFlow API] Merged: {len(merged_docs)} unique documents")
                print(f"[RAGFlow API] Paginated: page {page}, showing {len(paginated_docs)} of {merged_total} docs")
                print("=" * 80 + "\n")
                
                return {
                    "documents": paginated_docs,
                    "total": merged_total
                }
                
    except Exception as e:
        print(f"[RAGFlow API] Exception: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")
        return {"documents": [], "total": 0}


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


@router.get("/knowledge-upload")
async def api_get_knowledge_upload(request: Request):
    """获取文件列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    return {
        "success": True,
        "knowledge": knowledge_upload_db
    }


@router.post("/knowledge-upload")
async def api_add_knowledge_upload(request: Request, data: KnowledgeUploadRequest):
    """添加文件API接口（仅管理员）"""
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    new_knowledge = {
        "id": f"ku_{len(knowledge_upload_db) + 1:03d}",
        "title": data.title,
        "content": data.content,
        "priority": data.priority,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    knowledge_upload_db.append(new_knowledge)
    
    return {
        "success": True,
        "message": "文件添加成功",
        "knowledge": new_knowledge
    }


@router.post("/knowledge-upload-form")
async def api_add_knowledge_upload_form(
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
        "id": f"ku_{len(knowledge_upload_db) + 1:03d}",
        "title": title,
        "content": content,
        "priority": priority,
        "added_at": datetime.now().strftime("%Y-%m-%d")
    }
    
    knowledge_upload_db.append(new_knowledge)
    
    return RedirectResponse(url="/page/knowledge-upload", status_code=302)


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
