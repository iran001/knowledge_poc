"""
诊断和修复启动问题
"""
import subprocess
import sys
import socket
import time
import os


def check_port(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_process_on_port(port):
    """结束占用端口的进程"""
    try:
        # 查找占用端口的进程
        result = subprocess.run(
            ['netstat', '-ano', '|', 'findstr', f':{port}'],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if f':{port}' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        print(f"  结束进程 PID: {pid}")
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        return True
    except Exception as e:
        print(f"  结束进程失败: {e}")
    return False


def main():
    print("=" * 60)
    print("AI知识管理平台 - 启动诊断工具")
    print("=" * 60)
    print()

    # 检查端口占用情况
    print("[1/3] 检查端口占用情况...")
    port_8000 = check_port(8000)
    port_8501 = check_port(8501)
    
    if port_8000:
        print("  ⚠ 端口 8000 被占用，尝试结束进程...")
        kill_process_on_port(8000)
        time.sleep(1)
    else:
        print("  ✓ 端口 8000 可用")
        
    if port_8501:
        print("  ⚠ 端口 8501 被占用，尝试结束进程...")
        kill_process_on_port(8501)
        time.sleep(1)
    else:
        print("  ✓ 端口 8501 可用")
    print()

    # 检查依赖
    print("[2/3] 检查依赖...")
    try:
        import fastapi
        print("  ✓ fastapi 已安装")
    except:
        print("  ✗ fastapi 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "-q"])
        
    try:
        import streamlit
        print("  ✓ streamlit 已安装")
    except:
        print("  ✗ streamlit 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit", "-q"])
    print()

    # 启动服务
    print("[3/3] 启动服务...")
    print("  正在启动...")
    print()
    
    # 使用 start.py 启动
    current_dir = os.path.dirname(os.path.abspath(__file__))
    start_script = os.path.join(current_dir, "start.py")
    
    if os.path.exists(start_script):
        subprocess.run([sys.executable, start_script])
    else:
        print("  ✗ 未找到 start.py，请检查文件")


if __name__ == "__main__":
    main()
