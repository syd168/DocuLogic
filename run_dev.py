#!/usr/bin/env python3
"""
DocuLogic 开发环境管理脚本
用于统一启动/停止后端和前端服务

用法:
    python run_dev.py start   # 启动后端 + 前端
    python run_dev.py stop    # 停止后端 + 前端
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent
RUN_DIR = ROOT_DIR / ".run"
PID_FILE_BACKEND = RUN_DIR / ".backend.pid"
PID_FILE_FRONTEND = RUN_DIR / ".frontend.pid"

# 确保 .run 目录存在
RUN_DIR.mkdir(parents=True, exist_ok=True)


def get_python_executable():
    """获取 Python 可执行文件路径（优先使用虚拟环境）"""
    venv_python = ROOT_DIR / "venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def read_pid(pid_file):
    """读取 PID 文件"""
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # 检查进程是否还在运行
            if is_process_running(pid):
                return pid
            else:
                # 进程已不存在，删除过期的 PID 文件
                pid_file.unlink(missing_ok=True)
                return None
        except (ValueError, IOError):
            pid_file.unlink(missing_ok=True)
            return None
    return None


def is_process_running(pid):
    """检查进程是否在运行"""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def start_backend():
    """启动后端服务"""
    print("=" * 60)
    print("🚀 启动后端服务...")
    print("=" * 60)
    
    # 检查是否已经在运行
    existing_pid = read_pid(PID_FILE_BACKEND)
    if existing_pid:
        print(f"⚠️  后端服务已在运行 (PID: {existing_pid})")
        print(f"   API 地址: http://127.0.0.1:8000")
        return
    
    # 启动后端（后台运行）
    python_exe = get_python_executable()
    backend_script = ROOT_DIR / "web_server.py"
    
    # 创建日志文件
    log_dir = RUN_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    backend_log = log_dir / "backend.log"
    
    try:
        # 打开日志文件（覆盖模式，每次启动都从新日志开始）
        log_file = open(backend_log, 'w', encoding='utf-8')
        
        # 使用 nohup 或直接后台运行
        process = subprocess.Popen(
            [python_exe, str(backend_script)],
            cwd=str(ROOT_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,  # 将错误也输出到同一文件
            start_new_session=True  # 创建新的会话，使进程独立运行
        )
        
        print(f"✓ 后端服务正在启动...")
        print(f"  API 地址: http://127.0.0.1:8000")
        print(f"  API 文档: http://127.0.0.1:8000/api/docs")
        print(f"  日志文件: {backend_log}")
        print()
        
        # 等待几秒让后端启动并写入 PID 文件
        time.sleep(3)
        
        # 读取 web_server.py 写入的 PID 文件
        if PID_FILE_BACKEND.exists():
            with open(PID_FILE_BACKEND, 'r') as f:
                actual_pid = f.read().strip()
            print(f"  实际运行 PID: {actual_pid}")
        else:
            print(f"  ⚠️  警告：未找到 PID 文件")
        
    except Exception as e:
        print(f"✗ 后端启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def start_frontend():
    """启动前端服务"""
    print("=" * 60)
    print("🎨 启动前端服务...")
    print("=" * 60)
    
    # 检查是否已经在运行
    existing_pid = read_pid(PID_FILE_FRONTEND)
    if existing_pid:
        print(f"⚠️  前端服务已在运行 (PID: {existing_pid})")
        print(f"   前端地址: http://127.0.0.1:5173")
        return
    
    frontend_dir = ROOT_DIR / "frontend"
    if not frontend_dir.exists():
        print(f"✗ 前端目录不存在: {frontend_dir}")
        return
    
    try:
        # 检查 node_modules
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("⚠️  检测到前端依赖未安装，正在安装...")
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)
        
        # 创建日志文件
        log_dir = RUN_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        frontend_log = log_dir / "frontend.log"
        
        # 打开日志文件（覆盖模式，每次启动都从新日志开始）
        log_file = open(frontend_log, 'w', encoding='utf-8')
        
        # 启动前端（后台运行）
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            stdout=log_file,
            stderr=subprocess.STDOUT,  # 将错误也输出到同一文件
            start_new_session=True  # 创建新的会话，使进程独立运行
        )
        
        # 保存 PID
        with open(PID_FILE_FRONTEND, 'w') as f:
            f.write(str(process.pid))
        
        print(f"✓ 前端服务已启动 (PID: {process.pid})")
        print(f"  前端地址: http://127.0.0.1:5173")
        print(f"  日志文件: {frontend_log}")
        print()
        
    except Exception as e:
        print(f"✗ 前端启动失败: {e}")
        print("  提示: 可以手动在 frontend 目录下执行 'npm run dev'")


def stop_backend():
    """停止后端服务"""
    print("🛑 停止后端服务...",end="")
    
    pid = read_pid(PID_FILE_BACKEND)
    if pid:
        try:
            # 尝试优雅地终止进程
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            print(f"  发送终止信号到进程组 (PID: {pid})",end="")
            
            # 等待进程结束
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.5)
            
            # 如果还在运行，强制终止
            if is_process_running(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                print(f"  ,强制终止进程 (PID: {pid})",end="")
            
            print("✓ 后端服务已停止")
        except Exception as e:
            print(f"✗ 停止后端服务失败: {e}")
        finally:
            PID_FILE_BACKEND.unlink(missing_ok=True)
    else:
        print("  ℹ️  后端服务未运行")


def stop_frontend():
    """停止前端服务"""
    print("🛑 停止前端服务...",end="")
    
    pid = read_pid(PID_FILE_FRONTEND)
    if pid:
        try:
            # 尝试优雅地终止进程
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            print(f"  发送终止信号到进程组 (PID: {pid})",end="")
            
            # 等待进程结束
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.5)
            
            # 如果还在运行，强制终止
            if is_process_running(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                print(f"  ,强制终止进程 (PID: {pid})",end="")
            
            print("✓ 前端服务已停止")
        except Exception as e:
            print(f"✗ 停止前端服务失败: {e}")
        finally:
            PID_FILE_FRONTEND.unlink(missing_ok=True)
    else:
        print("  ℹ️  前端服务未运行")


def cmd_start():
    """启动命令"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "DocuLogic 开发环境启动" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 先停止可能正在运行的服务
    print("🔄 检查并停止已运行的服务...")
    stop_frontend()
    stop_backend()
    print()
    
    start_backend()
    start_frontend()
    
    print()
    print("=" * 60)
    print("✅ 所有服务已启动！")
    print("=" * 60)
    print()
    print("📌 访问地址:")
    print("   • 前端界面: http://127.0.0.1:5173")
    print("   • 后端 API: http://127.0.0.1:8000")
    print("   • API 文档: http://127.0.0.1:8000/api/docs")
    print()
    print("📝 日志文件:")
    print(f"   • 后端日志: {RUN_DIR / 'logs' / 'backend.log'}")
    print(f"   • 前端日志: {RUN_DIR / 'logs' / 'frontend.log'}")
    print()
    print("💡 提示:")
    print("   • 查看实时日志: tail -f .run/logs/backend.log")
    print("   • 按 Ctrl+C 不会停止服务，请使用 './stop.sh' 或 'python run_dev.py stop'")
    print()


def cmd_stop():
    """停止命令"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "DocuLogic 服务停止" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    stop_frontend()
    stop_backend()
    
    print()
    print("✅ 所有服务已停止")
    print()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python run_dev.py [start|stop]")
        print()
        print("命令:")
        print("  start   启动后端 + 前端服务")
        print("  stop    停止后端 + 前端服务")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        cmd_start()
    elif command == "stop":
        cmd_stop()
    else:
        print(f"✗ 未知命令: {command}")
        print("可用命令: start, stop")
        sys.exit(1)


if __name__ == "__main__":
    main()
