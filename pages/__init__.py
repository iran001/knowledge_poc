"""
页面模块
"""

from .login import render_login_page
from .chat import render_chat_page
from .documents import render_documents_page
from .hot_knowledge import render_hot_knowledge_page

__all__ = [
    'render_login_page',
    'render_chat_page',
    'render_documents_page',
    'render_hot_knowledge_page'
]
