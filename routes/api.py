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
import logging

from config import (
    SERVER_CONFIG, DIFY_CONFIG,
    ROLE_DISPLAY_MAP, ROLE_LEVEL_MAP, ROLE_PROMPT_MAP,
    MOCK_USERS, APP_INFO, PAGE_CONFIG, TEMPLATE_DIR,
    RAGFLOW_CONFIG, DIFY_UPLOADED_FILES
)
import os
import re
from fastapi import UploadFile, File
import glob
from fastapi.templating import Jinja2Templates
from data_store import sessions, knowledge_upload_db
from chat_history import save_chat_message, load_chat_history, get_user_conversations, delete_chat_history

# 获取日志记录器
logger = logging.getLogger(__name__)

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
    """聊天接口 - 代理转发到 Dify Chat API"""
    try:
        system_prompt = get_system_prompt_by_role(chat_data.role)
        
        base_url = str(DIFY_CONFIG.get("base_url", "")).rstrip("/")
        api_key = str(DIFY_CONFIG.get("api_key", ""))
        
        dify_payload = {
            "inputs": {"sys_prompt": system_prompt},
            "query": chat_data.message,
            "response_mode": "blocking",
            "conversation_id": chat_data.conversation_id or "",
            "user": f"user_{chat_data.role}",
            "files": []
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{base_url}/chat-messages"
        
        logger.info("=" * 60)
        logger.info("[Dify Chat API] REQUEST")
        logger.info(f"[Dify Chat API] URL: {url}")
        logger.info(f"[Dify Chat API] Headers: {json.dumps({'Authorization': 'Bearer ***', 'Content-Type': 'application/json'}, ensure_ascii=False)}")
        logger.info(f"[Dify Chat API] Payload: {json.dumps(dify_payload, ensure_ascii=False)[:500]}...")
        
        async with httpx.AsyncClient(timeout=float(DIFY_CONFIG.get("timeout", 30))) as client:
            response = await client.post(
                url,
                json=dify_payload,
                headers=headers
            )
            
            logger.info("[Dify Chat API] RESPONSE")
            logger.info(f"[Dify Chat API] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                dify_response = response.json()
                logger.info(f"[Dify Chat API] Response: {json.dumps(dify_response, ensure_ascii=False)[:500]}...")
                return {
                    "success": True,
                    "role": chat_data.role,
                    "system_prompt_injected": True,
                    "dify_response": dify_response
                }
            else:
                error_text = response.text
                logger.error(f"[Dify Chat API] Error: {response.status_code} - {error_text[:500]}")
                # Mock响应
                return {
                    "success": True,
                    "role": chat_data.role,
                    "system_prompt_injected": True,
                    "mock_mode": True,
                    "answer": f"【角色: {chat_data.role}】\n\n已注入对应角色的System Prompt。\n\n用户问题: {chat_data.message}"
                }
                
    except Exception as e:
        logger.error(f"[Dify Chat API] Exception: {e}")
        import traceback
        logger.error(f"[Dify Chat API] Traceback: {traceback.format_exc()}")
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
    
    logger.info("=" * 60)
    logger.info("[RAGFlow API] REQUEST - Fetch Single Dataset")
    logger.info(f"[RAGFlow API] Dataset ID: {dataset_id}")
    logger.info(f"[RAGFlow API] URL: {url}")
    logger.info(f"[RAGFlow API] Method: GET")
    logger.info(f"[RAGFlow API] Params: {json.dumps(params, ensure_ascii=False)}")
    logger.info(f"[RAGFlow API] Headers: {json.dumps({'Authorization': 'Bearer ***'}, ensure_ascii=False)}")
    
    response = await client.get(url, params=params, headers=headers)
    
    logger.info("[RAGFlow API] RESPONSE")
    logger.info(f"[RAGFlow API] Status Code: {response.status_code}")
    
    if response.status_code != 200:
        logger.error(f"[RAGFlow API] HTTP Error from dataset {dataset_id}: {response.status_code}")
        logger.error(f"[RAGFlow API] Error Response: {response.text[:500]}")
        return {"documents": [], "total": 0}
    
    data = response.json()
    logger.info(f"[RAGFlow API] Response Body: {json.dumps(data, ensure_ascii=False)[:1000]}...")
    
    if data.get("code") != 0:
        logger.error(f"[RAGFlow API] API Error from dataset {dataset_id}: code={data.get('code')}, message={data.get('message', 'Unknown')}")
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
    
    logger.info(f"[RAGFlow API] Dataset {dataset_id}: Fetched {len(documents)} documents, total: {total}")
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
    
    logger.info(f"[RAGFlow API] Starting fetch all documents from dataset: {dataset_id}")
    
    while True:
        result = await _fetch_single_dataset(
            client, base_url, dataset_id, api_key, keyword, page, page_size
        )
        
        docs = result.get("documents", [])
        if not docs:
            logger.info(f"[RAGFlow API] No more documents at page {page}")
            break
            
        all_docs.extend(docs)
        logger.info(f"[RAGFlow API] Page {page}: Added {len(docs)} docs, total collected: {len(all_docs)}")
        
        # 如果返回的数据少于 page_size，说明已经获取完毕
        if len(docs) < page_size:
            logger.info(f"[RAGFlow API] Last page reached at page {page}")
            break
            
        page += 1
        
        # 安全限制：最多获取 1000 条
        if len(all_docs) >= 1000:
            logger.warning(f"[RAGFlow API] Reached maximum limit (1000) for dataset {dataset_id}")
            break
    
    logger.info(f"[RAGFlow API] Completed fetch from dataset {dataset_id}: {len(all_docs)} documents total")
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
    logger.info("\n" + "=" * 80)
    logger.info("[RAGFlow API] fetch_documents_from_api START")
    logger.info(f"[RAGFlow API] Input params: role={role}, keyword={keyword}, page={page}, page_size={page_size}")
    
    try:
        base_url = str(RAGFLOW_CONFIG["base_url"])
        dataset_id = str(RAGFLOW_CONFIG["dataset_id"])
        vl_dataset_id = str(RAGFLOW_CONFIG.get("vl_dataset_id", ""))
        special_dataset_id = str(RAGFLOW_CONFIG.get("special_dataset_id", ""))
        api_key = str(RAGFLOW_CONFIG["api_key"])
        
        logger.info(f"[RAGFlow API] Configuration: base_url={base_url}, dataset_id={dataset_id}, vl_dataset_id={vl_dataset_id}, special_dataset_id={special_dataset_id}")
        
        async with httpx.AsyncClient(timeout=float(RAGFLOW_CONFIG.get("timeout", 60))) as client:
            
            if role == "reception":
                # reception 角色：从 dataset_id 和 special_dataset_id 获取数据
                logger.info(f"[RAGFlow API] Role is 'reception', fetching from dataset_id and special_dataset_id")
                
                docs_from_primary = await _fetch_all_documents_from_dataset(
                    client, base_url, dataset_id, api_key, keyword
                )
                docs_from_special = await _fetch_all_documents_from_dataset(
                    client, base_url, special_dataset_id, api_key, keyword
                )
                
                logger.info(f"[RAGFlow API] Primary dataset: {len(docs_from_primary)} docs")
                logger.info(f"[RAGFlow API] Special dataset: {len(docs_from_special)} docs")
                
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
                
                logger.info(f"[RAGFlow API] Merged: {len(merged_docs)} unique documents")
                logger.info(f"[RAGFlow API] Paginated: page {page}, showing {len(paginated_docs)} of {merged_total} docs")
                logger.info("=" * 80)
                
                return {
                    "documents": paginated_docs,
                    "total": merged_total
                }
            
            else:
                # admin/manager 角色：从三个 dataset 获取所有数据后合并
                logger.info(f"[RAGFlow API] Role is '{role}', fetching from all three datasets")
                
                docs_from_primary = await _fetch_all_documents_from_dataset(
                    client, base_url, dataset_id, api_key, keyword
                )
                docs_from_vl = await _fetch_all_documents_from_dataset(
                    client, base_url, vl_dataset_id, api_key, keyword
                )
                docs_from_special = await _fetch_all_documents_from_dataset(
                    client, base_url, special_dataset_id, api_key, keyword
                )
                
                logger.info(f"[RAGFlow API] Primary dataset: {len(docs_from_primary)} docs")
                logger.info(f"[RAGFlow API] VL dataset: {len(docs_from_vl)} docs")
                logger.info(f"[RAGFlow API] Special dataset: {len(docs_from_special)} docs")
                
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
                
                logger.info(f"[RAGFlow API] Merged: {len(merged_docs)} unique documents")
                logger.info(f"[RAGFlow API] Paginated: page {page}, showing {len(paginated_docs)} of {merged_total} docs")
                logger.info("=" * 80)
                
                return {
                    "documents": paginated_docs,
                    "total": merged_total
                }
                
    except Exception as e:
        logger.error(f"[RAGFlow API] Exception: {e}")
        logger.error(f"[RAGFlow API] Exception Type: {type(e).__name__}")
        import traceback
        logger.error(f"[RAGFlow API] Traceback: {traceback.format_exc()}")
        logger.info("=" * 80)
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


# =============================================================================
# 文档上传 API (带冲突检测)
# =============================================================================

# DIFY_UPLOADED_FILES 已从上方导入


async def upload_file_to_dify(file: UploadFile, file_content: bytes) -> Optional[str]:
    """
    上传文件到 Dify，获取 file_id
    
    Args:
        file: 上传的文件对象
        file_content: 文件内容字节
        
    Returns:
        成功返回 file_id，失败返回 None
    """
    try:
        base_url = str(DIFY_CONFIG.get("base_url", "")).rstrip("/")
        api_key = str(DIFY_CONFIG.get("api_key", ""))
        upload_endpoint = str(DIFY_CONFIG.get("upload_endpoint", "/files/upload"))
        
        url = f"{base_url}{upload_endpoint}"
        
        # 检测 MIME 类型
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file.filename or "")
        if not mime_type:
            ext = os.path.splitext(file.filename or "")[1].lower()
            mime_type = {
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.pdf': 'application/pdf',
                '.json': 'application/json',
                '.csv': 'text/csv'
            }.get(ext, 'application/octet-stream')
        
        logger.info("=" * 80)
        logger.info("[Dify File Upload] REQUEST")
        logger.info(f"[Dify File Upload] URL: {url}")
        logger.info(f"[Dify File Upload] Filename: {file.filename}")
        logger.info(f"[Dify File Upload] MIME Type: {mime_type}")
        logger.info(f"[Dify File Upload] File Size: {len(file_content)} bytes")
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # 使用 httpx 上传文件
        async with httpx.AsyncClient(timeout=60) as client:
            files = {
                'file': (file.filename, file_content, mime_type)
            }
            
            response = await client.post(url, headers=headers, files=files)
            
            logger.info("[Dify File Upload] RESPONSE")
            logger.info(f"[Dify File Upload] Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                file_id = data.get('id')
                if file_id:
                    logger.info(f"[Dify File Upload] Success, file_id: {file_id}")
                    return file_id
                else:
                    logger.error(f"[Dify File Upload] Response missing 'id' field: {data}")
                    return None
            else:
                logger.error(f"[Dify File Upload] HTTP Error: {response.status_code}")
                logger.error(f"[Dify File Upload] Error Response: {response.text[:500]}")
                return None
                
    except Exception as e:
        logger.error(f"[Dify File Upload] Exception: {e}")
        import traceback
        logger.error(f"[Dify File Upload] Traceback: {traceback.format_exc()}")
        return None


def build_conflict_check_payload(newfile_id: str, overfile_id: str) -> Dict[str, Any]:
    """
    构建冲突检查请求的 payload
    
    Args:
        newfile_id: 新上传文件的 Dify file_id
        overfile_id: 已有文件的 Dify file_id
        
    Returns:
        请求 payload 字典
    """
    return {
        "inputs": {
            "newfile": [
                {
                    "transfer_method": "local_file",
                    "upload_file_id": newfile_id,
                    "type": "document"
                }
            ],
            "overfile": [
                {
                    "transfer_method": "local_file",
                    "upload_file_id": overfile_id,
                    "type": "document"
                }
            ]
        },
        "user": "admin"
    }


async def call_dify_conflict_check_with_files(newfile_id: str, overfile_id: str) -> Dict[str, Any]:
    """
    调用 Dify 冲突检查接口 (使用 file_id)
    
    Args:
        newfile_id: 新上传文件的 Dify file_id
        overfile_id: 已有文件的 Dify file_id
        
    Returns:
        冲突检查结果字典
    """
    try:
        filecheck_endpoint = str(DIFY_CONFIG.get("filecheck_endpoint", ""))
        base_url = str(DIFY_CONFIG.get("base_url", "")).rstrip("/")
        api_key = str(DIFY_CONFIG.get("workflow_api_key", ""))
        
        # 构建完整 URL
        if not filecheck_endpoint.startswith("/"):
            filecheck_endpoint = "/" + filecheck_endpoint
        url = f"{base_url}{filecheck_endpoint}"
        
        payload = build_conflict_check_payload(newfile_id, overfile_id)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("=" * 80)
        logger.info("[Dify Conflict Check] REQUEST")
        logger.info(f"[Dify Conflict Check] URL: {url}")
        logger.info(f"[Dify Conflict Check] newfile_id: {newfile_id}")
        logger.info(f"[Dify Conflict Check] overfile_id: {overfile_id}")
        logger.info(f"[Dify Conflict Check] Payload: {json.dumps(payload, ensure_ascii=False)}")
        logger.info("=" * 80)
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            logger.info("[Dify Conflict Check] RESPONSE")
            logger.info(f"[Dify Conflict Check] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[Dify Conflict Check] Response Body: {json.dumps(data, ensure_ascii=False)[:2000]}...")
                
                # 解析响应
                parsed = parse_dify_workflow_response(data)
                return parsed
            else:
                error_text = response.text
                logger.error(f"[Dify Conflict Check] HTTP Error: {response.status_code}")
                logger.error(f"[Dify Conflict Check] Error Response: {error_text[:500]}")
                return {
                    "status": "true",
                    "conflict_point": "",
                    "conflict_reason": "",
                    "prompt": ""
                }
                
    except Exception as e:
        logger.error(f"[Dify Conflict Check] Exception: {e}")
        import traceback
        logger.error(f"[Dify Conflict Check] Traceback: {traceback.format_exc()}")
        return {
            "status": "true",
            "conflict_point": "",
            "conflict_reason": "",
            "prompt": ""
        }


def update_dify_uploaded_files(filename: str, file_id: str, conflict_filename: Optional[str] = None):
    """
    更新 DIFY_UPLOADED_FILES 配置
    
    Args:
        filename: 新上传的文件名
        file_id: 新上传文件的 Dify file_id
        conflict_filename: 如果替换了冲突文件，需要移除的文件名
    """
    try:
        # 先删除冲突文件记录（如果存在且不同于新文件名）
        if conflict_filename and conflict_filename in DIFY_UPLOADED_FILES and conflict_filename != filename:
            del DIFY_UPLOADED_FILES[conflict_filename]
            logger.info(f"[Config Update] Removed conflict file record: {conflict_filename}")
        
        # 更新内存中的配置（添加新文件记录）
        DIFY_UPLOADED_FILES[filename] = file_id
        
        # 更新 config.py 文件
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 构建新的配置字符串
        new_config = json.dumps(DIFY_UPLOADED_FILES, ensure_ascii=False, indent=4)
        
        # 使用正则表达式替换现有配置
        import re
        pattern = r'DIFY_UPLOADED_FILES: Dict\[str, str\] = \{[^}]*\}'
        replacement = f'DIFY_UPLOADED_FILES: Dict[str, str] = {new_config}'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 如果替换失败，尝试其他格式
        if new_content == content:
            pattern = r'DIFY_UPLOADED_FILES:.*?=.*?\{.*?\}'
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"[Config Update] Updated DIFY_UPLOADED_FILES: {filename} -> {file_id}")
        
    except Exception as e:
        logger.error(f"[Config Update] Error updating config: {e}")
        import traceback
        logger.error(f"[Config Update] Traceback: {traceback.format_exc()}")


def get_summary_file_content() -> str:
    """获取 summary 目录下的第一个文件内容 (保留兼容)"""
    summary_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "summary")
    
    logger.info(f"[Summary File] Looking for files in: {summary_dir}")
    
    if not os.path.exists(summary_dir):
        logger.warning(f"[Summary File] Directory not found: {summary_dir}")
        return ""
    
    # 获取所有文本文件
    text_files = []
    for ext in ['*.txt', '*.md', '*.doc', '*.docx', '*.pdf']:
        text_files.extend(glob.glob(os.path.join(summary_dir, ext)))
    
    logger.info(f"[Summary File] Found {len(text_files)} files: {text_files}")
    
    if not text_files:
        logger.warning("[Summary File] No text files found in summary directory")
        return ""
    
    # 读取第一个文件
    try:
        with open(text_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"[Summary File] Successfully read file: {text_files[0]}, length: {len(content)} chars")
            return content
    except Exception as e:
        logger.error(f"[Summary File] Error reading file {text_files[0]}: {e}")
        return ""


def parse_dify_workflow_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 Dify Workflow API 响应
    Dify Workflow 返回格式可能有多种情况:
    1. 标准格式: {"data": {"outputs": {...}}}
    2. 直接格式: {"outputs": {...}}
    3. 带 event 的流式格式: {"event": "workflow_finished", "data": {"outputs": {...}}}
    """
    outputs = None
    
    # 情况1: 标准嵌套格式 {"data": {"outputs": {...}}}
    if "data" in data and isinstance(data["data"], dict):
        if "outputs" in data["data"]:
            outputs = data["data"]["outputs"]
            logger.info(f"[Dify Response Parser] Found outputs in data.outputs")
    
    # 情况2: 直接格式 {"outputs": {...}}
    if outputs is None and "outputs" in data:
        outputs = data["outputs"]
        logger.info(f"[Dify Response Parser] Found outputs in root.outputs")
    
    # 情况3: event 格式 {"event": "...", "data": {"outputs": {...}}}
    if outputs is None and "event" in data:
        event_data = data.get("data", {})
        if isinstance(event_data, dict) and "outputs" in event_data:
            outputs = event_data["outputs"]
            logger.info(f"[Dify Response Parser] Found outputs in event data.outputs, event={data.get('event')}")
    
    # 情况4: 检查是否有 answer 字段 (Chat API 格式兼容)
    if outputs is None and "answer" in data:
        logger.info(f"[Dify Response Parser] Found answer field, treating as direct output")
        return {
            "status": "false" if "冲突" in str(data.get("answer", "")) else "true",
            "conflict_point": "",
            "conflict_reason": data.get("answer", ""),
            "prompt": data.get("answer", "")
        }
    
    if outputs:
        # 尝试从 outputs 中提取字段
        result = {
            "status": str(outputs.get("status", "true")).lower(),
            "conflict_point": outputs.get("conflict_point", ""),
            "conflict_reason": outputs.get("conflict_reason", ""),
            "prompt": outputs.get("prompt", outputs.get("text", outputs.get("answer", "")))
        }
        logger.info(f"[Dify Response Parser] Parsed outputs: {json.dumps(result, ensure_ascii=False)}")
        return result
    
    logger.warning(f"[Dify Response Parser] Could not find outputs in response, keys: {list(data.keys())}")
    return {
        "status": "true",
        "conflict_point": "",
        "conflict_reason": "",
        "prompt": ""
    }


async def call_dify_conflict_check(new_file_content: str, existing_file_content: str) -> Dict[str, Any]:
    """调用 Dify 冲突检查接口 (Workflow API)"""
    try:
        filecheck_endpoint = str(DIFY_CONFIG.get("filecheck_endpoint", ""))
        base_url = str(DIFY_CONFIG.get("base_url", ""))
        api_key = str(DIFY_CONFIG.get("workflow_api_key", ""))
        
        # 构建完整 URL (确保 base_url 不以 / 结尾，endpoint 以 / 开头)
        base_url = base_url.rstrip("/")
        if not filecheck_endpoint.startswith("/"):
            filecheck_endpoint = "/" + filecheck_endpoint
        url = f"{base_url}{filecheck_endpoint}"
        
        # Dify Workflow API 请求体
        # 注意: inputs 的值类型需要与 Workflow 中定义的变量类型一致
        payload = {
            "inputs": {
                "newfile": new_file_content,  # 改为字符串而非数组
                "overfile": existing_file_content  # 改为字符串而非数组
            },
            "response_mode": "blocking",  # Workflow 支持 blocking 和 streaming
            "user": "admin"
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 记录请求日志（脱敏处理）
        logger.info("=" * 80)
        logger.info("[Dify Workflow] REQUEST")
        logger.info(f"[Dify Workflow] URL: {url}")
        logger.info(f"[Dify Workflow] Method: POST")
        logger.info(f"[Dify Workflow] Headers: {json.dumps({'Authorization': 'Bearer ***', 'Content-Type': 'application/json'}, ensure_ascii=False)}")
        logger.info(f"[Dify Workflow] Payload Summary: newfile_length={len(new_file_content)}, overfile_length={len(existing_file_content)}")
        logger.info(f"[Dify Workflow] Payload: {json.dumps(payload, ensure_ascii=False)[:2000]}...")
        logger.info("=" * 80)
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            # 记录响应日志
            logger.info("[Dify Workflow] RESPONSE")
            logger.info(f"[Dify Workflow] Status Code: {response.status_code}")
            logger.info(f"[Dify Workflow] Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 处理可能的流式响应 (SSE 格式)
                content_type = response.headers.get("content-type", "")
                
                if "text/event-stream" in content_type or "application/x-ndjson" in content_type:
                    # 处理流式响应
                    logger.info(f"[Dify Workflow] Detected streaming response")
                    text = response.text
                    logger.info(f"[Dify Workflow] Raw streaming response: {text[:2000]}...")
                    
                    # 解析 SSE 格式数据
                    last_data = None
                    for line in text.strip().split("\n"):
                        line = line.strip()
                        if line.startswith("data:"):
                            try:
                                data_json = line[5:].strip()
                                data = json.loads(data_json)
                                last_data = data
                                # 如果是 workflow_finished 事件，提取最终结果
                                if data.get("event") == "workflow_finished":
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    if last_data:
                        parsed = parse_dify_workflow_response(last_data)
                        if parsed:
                            return parsed
                else:
                    # 普通 JSON 响应
                    data = response.json()
                    logger.info(f"[Dify Workflow] Response Body: {json.dumps(data, ensure_ascii=False)[:2000]}...")
                    
                    parsed = parse_dify_workflow_response(data)
                    if parsed:
                        return parsed
                
                # 解析失败，返回默认值
                logger.warning(f"[Dify Workflow] Could not parse response, using default")
                return {
                    "status": "true",
                    "conflict_point": "",
                    "conflict_reason": "",
                    "prompt": ""
                }
            else:
                error_text = response.text
                logger.error(f"[Dify Workflow] HTTP Error: {response.status_code}")
                logger.error(f"[Dify Workflow] Error Response: {error_text[:1000]}")
                # 如果接口调用失败，默认允许上传
                return {
                    "status": "true",
                    "conflict_point": "",
                    "conflict_reason": "",
                    "prompt": ""
                }
    except httpx.TimeoutException as e:
        logger.error(f"[Dify Workflow] Timeout Error: {e}")
        return {
            "status": "true",
            "conflict_point": "",
            "conflict_reason": "",
            "prompt": ""
        }
    except Exception as e:
        logger.error(f"[Dify Workflow] Exception: {e}")
        logger.error(f"[Dify Workflow] Exception Type: {type(e).__name__}")
        import traceback
        logger.error(f"[Dify Workflow] Traceback: {traceback.format_exc()}")
        # 发生异常时默认允许上传
        return {
            "status": "true",
            "conflict_point": "",
            "conflict_reason": "",
            "prompt": ""
        }


async def upload_to_ragflow(file: UploadFile, file_content: bytes) -> Dict[str, Any]:
    """上传文件到 RAGFlow"""
    try:
        base_url = str(RAGFLOW_CONFIG.get("base_url", ""))
        api_key = str(RAGFLOW_CONFIG.get("api_key", ""))
        dataset_id = str(RAGFLOW_CONFIG.get("dataset_id", ""))
        
        url = f"{base_url}/datasets/{dataset_id}/documents"
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # 准备文件
        files = {
            "file": (file.filename, file_content, file.content_type or "application/octet-stream")
        }
        
        # 可选：解析配置
        data = {
            "parser_config": '{"chunk_token_num": 512, "layout_recognize": true}'
        }
        
        # 记录请求日志（脱敏处理）
        logger.info("=" * 80)
        logger.info("[RAGFlow Upload] REQUEST")
        logger.info(f"[RAGFlow Upload] URL: {url}")
        logger.info(f"[RAGFlow Upload] Method: POST")
        logger.info(f"[RAGFlow Upload] Headers: {json.dumps({'Authorization': 'Bearer ***'}, ensure_ascii=False)}")
        logger.info(f"[RAGFlow Upload] Filename: {file.filename}")
        logger.info(f"[RAGFlow Upload] Content-Type: {file.content_type}")
        logger.info(f"[RAGFlow Upload] File Size: {len(file_content)} bytes")
        logger.info(f"[RAGFlow Upload] Parser Config: {data['parser_config']}")
        logger.info("=" * 80)
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, files=files, data=data)
            
            # 记录响应日志
            logger.info("[RAGFlow Upload] RESPONSE")
            logger.info(f"[RAGFlow Upload] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[RAGFlow Upload] Response Body: {json.dumps(result, ensure_ascii=False)[:2000]}...")
                logger.info("[RAGFlow Upload] Upload successful")
                return {
                    "success": True,
                    "data": result
                }
            else:
                error_text = response.text
                logger.error(f"[RAGFlow Upload] HTTP Error: {response.status_code}")
                logger.error(f"[RAGFlow Upload] Error Response: {error_text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}"
                }
    except Exception as e:
        logger.error(f"[RAGFlow Upload] Exception: {e}")
        logger.error(f"[RAGFlow Upload] Exception Type: {type(e).__name__}")
        import traceback
        logger.error(f"[RAGFlow Upload] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/upload-document")
async def api_upload_document(
    request: Request,
    file: UploadFile = File(...),
    force_replace: str = Form("false"),
    conflict_file: str = Form("")  # 指定要替换的冲突文件名
):
    """
    上传文档到知识库 (新流程)
    1. 上传文件到 Dify 获取 file_id
    2. 使用 file_id 调用 Dify 冲突检查接口与已有文件比较
    3. 如果有冲突且用户未确认替换，返回冲突信息
    4. 如果没有冲突或用户确认替换，上传到 RAGFlow
    5. 更新 DIFY_UPLOADED_FILES 记录
    """
    user = get_current_user(request)
    if not user:
        logger.warning("[Upload Document] Unauthorized access attempt")
        raise HTTPException(status_code=401, detail="未登录")
    
    logger.info("=" * 80)
    logger.info("[Upload Document] START")
    logger.info(f"[Upload Document] User: {user.get('username')} ({user.get('role')})")
    logger.info(f"[Upload Document] Filename: {file.filename}")
    logger.info(f"[Upload Document] Force Replace: {force_replace}")
    logger.info(f"[Upload Document] Conflict File: {conflict_file}")
    
    # 检查文件类型
    allowed_extensions = ['.txt', '.pdf', '.doc', '.docx', '.md']
    filename = file.filename or ""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        logger.error(f"[Upload Document] Invalid file type: {file_ext}")
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型，请上传: {', '.join(allowed_extensions)}"
        )
    
    try:
        # 读取文件内容
        file_content = await file.read()
        logger.info(f"[Upload Document] File read successful, size: {len(file_content)} bytes")
        
        # 步骤1: 上传文件到 Dify 获取 file_id
        logger.info("[Upload Document] Step 1: Uploading file to Dify...")
        newfile_id = await upload_file_to_dify(file, file_content)
        
        if not newfile_id:
            logger.error("[Upload Document] Failed to upload file to Dify")
            raise HTTPException(status_code=500, detail="文件上传到 Dify 失败")
        
        logger.info(f"[Upload Document] File uploaded to Dify, file_id: {newfile_id}")
        
        # 步骤2: 检查是否已有上传的文件记录
        if not DIFY_UPLOADED_FILES:
            logger.info("[Upload Document] No existing files in DIFY_UPLOADED_FILES, uploading directly to RAGFlow")
            # 上传到 RAGFlow
            await file.seek(0)
            file_content = await file.read()
            upload_result = await upload_to_ragflow(file, file_content)
            
            if upload_result["success"]:
                # 更新配置
                update_dify_uploaded_files(filename, newfile_id)
                logger.info("[Upload Document] Direct upload successful (first file)")
                return {
                    "success": True,
                    "message": "文件上传成功",
                    "filename": file.filename
                }
            else:
                logger.error(f"[Upload Document] Upload failed: {upload_result.get('error')}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
                )
        
        # 步骤3: 强制替换模式
        if force_replace.lower() == "true":
            logger.info(f"[Upload Document] Force replace mode, replacing: {conflict_file}")
            
            # 上传到 RAGFlow
            await file.seek(0)
            file_content = await file.read()
            upload_result = await upload_to_ragflow(file, file_content)
            
            if upload_result["success"]:
                # 更新配置，移除冲突文件记录
                update_dify_uploaded_files(filename, newfile_id, conflict_file if conflict_file else None)
                logger.info("[Upload Document] Force replace upload successful")
                return {
                    "success": True,
                    "message": "文件已成功替换并上传到知识库",
                    "filename": file.filename
                }
            else:
                logger.error(f"[Upload Document] Force replace upload failed: {upload_result.get('error')}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
                )
        
        # 步骤4: 依次与已有文件进行冲突检查（一旦检测到冲突立即停止）
        logger.info(f"[Upload Document] Step 4: Checking conflicts with {len(DIFY_UPLOADED_FILES)} existing files...")
        
        for existing_filename, existing_file_id in DIFY_UPLOADED_FILES.items():
            logger.info(f"[Upload Document] Checking conflict with: {existing_filename} (id: {existing_file_id})")
            
            conflict_result = await call_dify_conflict_check_with_files(newfile_id, existing_file_id)
            
            if conflict_result.get("status") == "false":
                logger.info(f"[Upload Document] Conflict detected with {existing_filename}, stopping conflict check")
                # 立即返回冲突信息给前端
                return {
                    "success": False,
                    "conflict": True,
                    "status": "false",
                    "conflict_point": conflict_result.get("conflict_point", ""),
                    "conflict_reason": conflict_result.get("conflict_reason", ""),
                    "prompt": conflict_result.get("prompt", "检测到文件冲突"),
                    "conflict_file": existing_filename,
                    "conflict_count": 1
                }
        
        # 步骤5: 没有冲突，上传到 RAGFlow
        logger.info("[Upload Document] No conflict detected, proceeding to upload to RAGFlow")
        await file.seek(0)
        file_content = await file.read()
        upload_result = await upload_to_ragflow(file, file_content)
        
        if upload_result["success"]:
            # 更新配置，记录新文件
            update_dify_uploaded_files(filename, newfile_id)
            logger.info("[Upload Document] Upload successful")
            return {
                "success": True,
                "message": "文件上传成功",
                "filename": file.filename
            }
        else:
            logger.error(f"[Upload Document] Upload failed: {upload_result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upload Document] Exception: {e}")
        logger.error(f"[Upload Document] Exception Type: {type(e).__name__}")
        import traceback
        logger.error(f"[Upload Document] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
