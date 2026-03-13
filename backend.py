"""
IHG智能问答平台 - FastAPI 后端
使用Jinja2模板引擎和配置文件
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入配置文件
from config import SERVER_CONFIG, APP_INFO

# 导入路由
from routes import pages_router, api_router

# =============================================================================
# FastAPI 应用实例
# =============================================================================
app = FastAPI(
    title=APP_INFO["name"],
    description="支持RBAC权限控制和动态Prompt注入的AI知识管理后端",
    version=APP_INFO["version"]
)

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
# 注册路由
# =============================================================================
app.include_router(pages_router)
app.include_router(api_router)

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
        host=str(SERVER_CONFIG["host"]),
        port=int(SERVER_CONFIG["backend_port"]),
        reload=bool(SERVER_CONFIG["reload"])
    )
