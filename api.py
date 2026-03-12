"""
API 调用封装模块
"""

import requests
from typing import Dict, Any
from config import API_BASE_URL


def api_login(username: str, password: str) -> Dict[str, Any]:
    """调用后端登录接口"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/login",
            json={"username": username, "password": password},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"网络错误: {str(e)}"}


def api_chat(role: str, message: str) -> Dict[str, Any]:
    """调用后端聊天接口（由后端转发到Dify）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={"role": role, "message": message},
            timeout=60
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


def api_get_documents(role: str, keyword: str = "") -> Dict[str, Any]:
    """调用后端文档列表接口"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/documents",
            json={"role": role, "search_keyword": keyword if keyword else None},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}


def api_add_hot_knowledge(role: str, title: str, content: str) -> Dict[str, Any]:
    """调用后端添加热知识接口（仅管理员）"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/hot-knowledge?role={role}",
            json={"title": title, "content": content, "priority": "high"},
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": f"请求失败: {str(e)}"}
