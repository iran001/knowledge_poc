"""
API路由 - RESTful API接口
只保留路由定义，业务逻辑委托给服务模块
"""

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

from config import (
    ROLE_DISPLAY_MAP, ROLE_LEVEL_MAP, ROLE_PROMPT_MAP,
    MOCK_USERS, APP_INFO, PAGE_CONFIG, TEMPLATE_DIR,
    DIFY_UPLOADED_FILES
)
import os
from fastapi import UploadFile, File
from fastapi.templating import Jinja2Templates

from data_store import sessions, knowledge_upload_db
from chat_history import save_chat_message, load_chat_history, get_user_conversations, delete_chat_history

# 导入服务模块
from services import (
    upload_file_to_dify,
    call_dify_conflict_check_with_files,
    fetch_documents_from_api,
    upload_to_ragflow,
    update_dify_uploaded_files,
)


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
# 认证 API
# =============================================================================

@router.post("/login")
async def api_login(request: Request, login_data: LoginRequest):
    """API登录接口"""
    user = MOCK_USERS.get(login_data.username)
    
    if not user or user["password"] != login_data.password:
        return {"success": False, "message": "用户名或密码错误"}
    
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"]
    }
    
    response = {
        "success": True,
        "message": "登录成功",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "display_name": user["display_name"]
        }
    }
    
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


# =============================================================================
# 聊天 API
# =============================================================================

@router.post("/chat")
async def api_chat(request: Request, chat_data: ChatRequest):
    """聊天接口 - 代理转发到 Dify Chat API"""
    from services.dify_service import call_dify_chat
    
    system_prompt = get_system_prompt_by_role(chat_data.role)
    return await call_dify_chat(
        role=chat_data.role,
        message=chat_data.message,
        conversation_id=chat_data.conversation_id or "",
        system_prompt=system_prompt
    )


# =============================================================================
# 文档 API
# =============================================================================

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


# =============================================================================
# 知识上传 API
# =============================================================================

@router.get("/knowledge-upload")
async def api_get_knowledge_upload(request: Request):
    """获取文件列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    return {"success": True, "knowledge": knowledge_upload_db}


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
    
    return {"success": True, "message": "文件添加成功", "knowledge": new_knowledge}


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
    
    return {"success": success, "conversation_id": data.conversation_id}


@router.get("/chat-history/{conversation_id}")
async def api_get_chat_history(request: Request, conversation_id: str):
    """获取对话历史"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    history = load_chat_history(conversation_id)
    
    user_history = [
        msg for msg in history 
        if msg.get("metadata", {}).get("user_id") == user.get("username")
    ]
    
    return {"success": True, "conversation_id": conversation_id, "history": user_history}


@router.get("/chat-history")
async def api_get_user_conversations(request: Request):
    """获取用户的所有会话列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    conversations = get_user_conversations(user.get("username"))
    
    return {"success": True, "conversations": conversations}


@router.delete("/chat-history/{conversation_id}")
async def api_delete_chat_history(request: Request, conversation_id: str):
    """删除对话历史"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    history = load_chat_history(conversation_id)
    user_messages = [m for m in history if m.get("metadata", {}).get("user_id") == user.get("username")]
    
    if not user_messages:
        raise HTTPException(status_code=403, detail="无权删除此对话")
    
    success = delete_chat_history(conversation_id)
    
    return {"success": success, "conversation_id": conversation_id}


# =============================================================================
# 文档上传 API (带冲突检测)
# =============================================================================

ALLOWED_EXTENSIONS = ['.txt', '.pdf', '.doc', '.docx', '.md']


@router.post("/upload-document")
async def api_upload_document(
    request: Request,
    file: UploadFile = File(...),
    force_replace: str = Form("false"),
    conflict_file: str = Form("")  # 指定要替换的冲突文件名
):
    """
    上传文档到知识库
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
    
    _log_upload_start(user, file, force_replace, conflict_file)
    
    filename = file.filename or ""
    _validate_file_extension(filename)
    
    try:
        # 读取文件内容
        file_content = await file.read()
        logger.info(f"[Upload Document] File read successful, size: {len(file_content)} bytes")
        
        # 步骤1: 上传文件到 Dify 获取 file_id
        logger.info("[Upload Document] Step 1: Uploading file to Dify...")
        dify_result = await upload_file_to_dify(file, file_content)
        
        if not dify_result.get("success"):
            error_msg = dify_result.get("error", "未知错误")
            logger.error(f"[Upload Document] Failed to upload file to Dify: {error_msg}")
            raise HTTPException(status_code=500, detail=f"上传知识库失败: {error_msg}")
        
        newfile_id = str(dify_result.get("file_id", ""))
        if not newfile_id:
            logger.error("[Upload Document] Dify returned empty file_id")
            raise HTTPException(status_code=500, detail="上传知识库失败: 返回的 file_id 为空")
        
        logger.info(f"[Upload Document] File uploaded to Dify, file_id: {newfile_id}")
        
        # 步骤2: 首次上传直接处理
        if not DIFY_UPLOADED_FILES:
            return await _handle_first_upload(file, file_content, filename, newfile_id)
        
        # 步骤3: 强制替换模式
        if force_replace.lower() == "true":
            return await _handle_force_replace(file, file_content, filename, newfile_id, conflict_file)
        
        # 步骤4: 冲突检查（传入文件内容用于本地相似度计算）
        try:
            new_file_text = file_content.decode('utf-8', errors='ignore')
        except:
            new_file_text = ""
        conflict_response = await _check_conflicts(newfile_id, filename, new_file_text)
        if conflict_response:
            return conflict_response
        
        # 步骤5: 上传到 RAGFlow
        return await _upload_to_ragflow_and_save(file, file_content, filename, newfile_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upload Document] Exception: {e}")
        logger.error(f"[Upload Document] Exception Type: {type(e).__name__}")
        import traceback
        logger.error(f"[Upload Document] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


def _log_upload_start(user: Dict[str, Any], file: UploadFile, force_replace: str, conflict_file: str):
    """记录上传开始日志"""
    logger.info("=" * 80)
    logger.info("[Upload Document] START")
    logger.info(f"[Upload Document] User: {user.get('username')} ({user.get('role')})")
    logger.info(f"[Upload Document] Filename: {file.filename}")
    logger.info(f"[Upload Document] Force Replace: {force_replace}")
    logger.info(f"[Upload Document] Conflict File: {conflict_file}")


def _validate_file_extension(filename: str):
    """验证文件扩展名"""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.error(f"[Upload Document] Invalid file type: {file_ext}")
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型，请上传: {', '.join(ALLOWED_EXTENSIONS)}"
        )


async def _handle_first_upload(file: UploadFile, file_content: bytes, filename: str, newfile_id: str):
    """处理首次上传（无已有文件）"""
    logger.info("[Upload Document] No existing files in DIFY_UPLOADED_FILES, uploading directly to RAGFlow")
    
    await file.seek(0)
    file_content = await file.read()
    upload_result = await upload_to_ragflow(file, file_content)
    
    if upload_result["success"]:
        update_dify_uploaded_files(filename, newfile_id)
        logger.info("[Upload Document] Direct upload successful (first file)")
        return {"success": True, "message": "文件上传成功", "filename": file.filename}
    else:
        logger.error(f"[Upload Document] Upload failed: {upload_result.get('error')}")
        raise HTTPException(
            status_code=500, 
            detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
        )


async def _handle_force_replace(
    file: UploadFile, 
    file_content: bytes, 
    filename: str, 
    newfile_id: str, 
    conflict_file: str
):
    """处理强制替换模式"""
    logger.info(f"[Upload Document] Force replace mode, replacing: {conflict_file}")
    
    await file.seek(0)
    file_content = await file.read()
    upload_result = await upload_to_ragflow(file, file_content)
    
    if upload_result["success"]:
        update_dify_uploaded_files(filename, newfile_id, conflict_file if conflict_file else None)
        logger.info("[Upload Document] Force replace upload successful")
        return {"success": True, "message": "文件已成功替换并上传到知识库", "filename": file.filename}
    else:
        logger.error(f"[Upload Document] Force replace upload failed: {upload_result.get('error')}")
        raise HTTPException(
            status_code=500, 
            detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
        )


async def _check_conflicts(
    newfile_id: str,
    _filename: str,
    _new_file_content: str
) -> Optional[Dict[str, Any]]:
    """
    检查文件冲突（直接调用 Dify 接口与所有已有文件进行比较）
    
    流程：
    遍历 DIFY_UPLOADED_FILES 中的所有文件，依次调用 Dify 进行冲突检查
    一旦检测到冲突立即停止
    
    返回: 有冲突时返回冲突响应，无冲突返回 None
    """
    logger.info(f"[Upload Document] Step 4: Checking conflicts with {len(DIFY_UPLOADED_FILES)} existing files...")
    logger.info("[Upload Document] Using direct Dify conflict check for all existing files")
    
    for existing_filename, existing_file_id in DIFY_UPLOADED_FILES.items():
        logger.info(f"[Upload Document] Checking conflict with: {existing_filename} (id: {existing_file_id})")
        
        conflict_result = await call_dify_conflict_check_with_files(newfile_id, existing_file_id)
        
        if conflict_result.get("status") == "false":
            logger.info(f"[Upload Document] Conflict detected with {existing_filename}, stopping conflict check")
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
    
    logger.info(f"[Upload Document] No conflict detected after checking {len(DIFY_UPLOADED_FILES)} files")
    return None


async def _upload_to_ragflow_and_save(file: UploadFile, file_content: bytes, filename: str, newfile_id: str):
    """上传到 RAGFlow 并保存配置"""
    logger.info("[Upload Document] No conflict detected, proceeding to upload to RAGFlow")
    
    await file.seek(0)
    file_content = await file.read()
    upload_result = await upload_to_ragflow(file, file_content)
    
    if upload_result["success"]:
        update_dify_uploaded_files(filename, newfile_id)
        logger.info("[Upload Document] Upload successful")
        return {"success": True, "message": "文件上传成功", "filename": file.filename}
    else:
        logger.error(f"[Upload Document] Upload failed: {upload_result.get('error')}")
        raise HTTPException(
            status_code=500, 
            detail=f"上传到知识库失败: {upload_result.get('error', '未知错误')}"
        )


# =============================================================================
# 链接代理 API - 用于访问需要 api_key 的外部链接
# =============================================================================

class ProxyLinkRequest(BaseModel):
    """代理链接请求"""
    url: str


@router.post("/proxy-link")
async def proxy_link(request: ProxyLinkRequest):
    """
    代理访问外部链接，自动添加 Ragflow api_key 到 header
    用于支持 [text](url) 格式的链接点击访问
    """
    import httpx
    from config import RAGFLOW_CONFIG
    
    target_url = request.url
    api_key = str(RAGFLOW_CONFIG.get("api_key", ""))
    
    logger.info(f"[Proxy Link] Proxying request to: {target_url}, api_key: {api_key}")
    
    try:
        # 使用 GET 方式访问目标 URL，添加 Authorization header
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(target_url, headers=headers)
            
            logger.info(f"[Proxy Link] Response status: {response.status_code}")
            logger.info(f"[Proxy Link] Response headers: {dict(response.headers)}")
            
            # 从 Content-Disposition header 中提取文件名
            original_filename = None
            content_disposition = response.headers.get("Content-Disposition", "")
            if content_disposition:
                # 解析 filename="xxx" 或 filename*=UTF-8''xxx
                import re
                # 优先匹配 filename="..." 或 filename='...' 引号内的所有内容
                filename_match = re.search(r'filename=[\'"]([^\'"]*)[\'"]', content_disposition, re.IGNORECASE)
                if not filename_match:
                    # 尝试匹配 filename*=UTF-8''xxx 格式
                    filename_match = re.search(r'filename\*=[\'"]?(?:UTF-8[\'"]{0,3})?([^;\s]+)', content_disposition, re.IGNORECASE)
                if filename_match:
                    original_filename = filename_match.group(1)
                    # URL decode if needed
                    try:
                        from urllib.parse import unquote
                        original_filename = unquote(original_filename)
                    except:
                        pass
            
            # 如果 header 中没有 filename，从 URL 路径提取
            if not original_filename:
                from urllib.parse import urlparse, unquote
                parsed_url = urlparse(target_url)
                path_parts = parsed_url.path.split('/')
                if path_parts and path_parts[-1]:
                    original_filename = unquote(path_parts[-1])
            
            logger.info(f"[Proxy Link] Original filename: {original_filename}")
            
            # 获取响应的 Content-Type
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            # 如果响应是 JSON 格式，说明可能是错误信息，返回给前端显示
            if "application/json" in content_type:
                try:
                    json_data = response.json()
                    error_msg = json_data.get("message") or json_data.get("error") or str(json_data)
                    logger.error(f"[Proxy Link] Target returned JSON error: {error_msg}")
                    raise HTTPException(status_code=400, detail=f"目标接口返回错误: {error_msg}")
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"[Proxy Link] Failed to parse JSON response: {e}")
                    raise HTTPException(status_code=400, detail="目标接口返回错误数据")
            
            # 返回响应内容，附加原始文件名到自定义 header（用于文件下载）
            from fastapi.responses import Response
            from urllib.parse import quote
            response_headers = {
                "Content-Type": content_type
            }
            if original_filename:
                # 对文件名进行 URL 编码，避免中文导致的 latin-1 编码错误
                encoded_filename = quote(original_filename, safe='')
                response_headers["X-Original-Filename"] = encoded_filename
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers
            )
            
    except httpx.TimeoutException:
        logger.error("[Proxy Link] Request timeout")
        raise HTTPException(status_code=504, detail="请求超时")
    except Exception as e:
        logger.error(f"[Proxy Link] Error: {e}")
        raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")
