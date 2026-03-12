"""
IHG智能问答平台 - 统一启动脚本
同时启动 FastAPI 后端和 Streamlit 前端
"""

import subprocess
import sys
import time
import os
import signal
import atexit

# 存储子进程
processes = []


def cleanup():
    """清理所有子进程"""
    print("\n正在关闭所有服务...")
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
    print("所有服务已关闭")


def start_backend():
    """启动 FastAPI 后端"""
    cmd = [sys.executable, "-m", "uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
    return subprocess.Popen(cmd)


def start_frontend():
    """启动 Streamlit 前端"""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend.py",
        "--server.port", "8501",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--browser.gatherUsageStats", "false"
    ]
    # 将输出重定向到文件以便调试
    log_file = open("streamlit.log", "w")
    return subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 15 + "IHG智能问答平台 - 统一启动脚本")
    print("=" * 70)
    print()
    
    # 注册清理函数
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    # 启动后端
    print("[1/2] 正在启动 FastAPI 后端服务...")
    backend_process = start_backend()
    processes.append(backend_process)
    time.sleep(2)
    print(f"      ✓ 后端服务已启动: http://localhost:8000")
    print()
    
    # 启动前端
    print("[2/2] 正在启动 Streamlit 前端服务...")
    frontend_process = start_frontend()
    processes.append(frontend_process)
    time.sleep(3)
    print(f"      ✓ 前端服务已启动: http://localhost:8501")
    print()
    
    print("-" * 70)
    print("访问地址:")
    print(f"  • 统一入口:  http://localhost:8000")
    print(f"  • 前端直访:  http://localhost:8501")
    print(f"  • API文档:   http://localhost:8000/docs")
    print(f"  • ReDoc:     http://localhost:8000/redoc")
    print("-" * 70)
    print()
    print("按 Ctrl+C 停止所有服务")
    print("=" * 70)
    
    # 等待进程结束
    try:
        while True:
            time.sleep(1)
            # 检查进程是否还在运行
            for process in processes[:]:
                if process.poll() is not None:
                    print(f"\n进程已退出 (返回码: {process.returncode})")
                    return
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")


if __name__ == "__main__":
    main()
