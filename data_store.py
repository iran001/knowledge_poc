"""
数据存储模块 - 共享内存数据存储
用于在生产环境迁移到Redis/数据库前的临时存储
"""

from typing import Dict, Any, List
from config import MOCK_HOT_KNOWLEDGE

# 会话存储
sessions: Dict[str, Dict[str, Any]] = {}

# 热知识数据
hot_knowledge_db: List[Dict[str, Any]] = MOCK_HOT_KNOWLEDGE.copy()
