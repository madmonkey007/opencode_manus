#!/usr/bin/env python3
"""
OpenCode 服务器管理器

自动管理服务器生命周期和测试
"""

import subprocess
import sys
import time
import os
import signal
import requests
from pathlib import Path


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{msg}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")


def print_success(msg):
    print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {msg}")


def print_error(msg):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")


def print_info(msg):
    print(f"{Colors.OKCYAN}[INFO]{Colors.ENDC} {msg}")


def print_warning(msg):
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")


class ServerManager:
    """服务器管理器"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.base_dir = Path(base_dir)
        self.server_process = None
        self.base_url = "http://localhost:8088"

    def stop_all_servers(self):
        """停止所有 Python 服务器"""
        print_header("停止旧服务")

        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", "python.exe"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print_success("已停止所有 Python 进程")
                else:
                    print_info("没有运行的 Python 进程")
            except Exception as e:
                print_warning(f"停止进程失败: {e}")
        else:
            try:
                # Linux/Mac
                subprocess.run(
                    ["pkill", "-9", "-f", "app.main"],
                    capture_output=True
                )
                print_success("已停止所有 Python 进程")
            except Exception as e:
                print_warning(f"停止进程失败: {e}")

        # 等待端口释放
        print_info("等待端口释放...")
        time.sleep(2)

    def start_server(self):
        """启动服务器"""
        print_header("启动服务器")

        log_file = self.base_dir / "server.log"

        try:
            # 启动服务器进程
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "app.main"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            print_success(f"服务器进程已启动 (PID: {self.server_process.pid})")
            print_info(f"日志文件: {log_file}")

            # 等待服务器启动
            print_info("等待服务器初始化...")
            time.sleep(5)

            # 检查服务器是否正常
            if self.is_server_ready():
                print_success("服务器已就绪")
                return True
            else:
                print_error("服务器启动失败")
                return False

        except Exception as e:
            print_error(f"启动服务器失败: {e}")
            return False

    def is_server_ready(self) -> bool:
        """检查服务器是否就绪"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=2)
            return response.status_code == 200
        except:
            return False

    def run_test(self, test_type: str = "quick"):
        """运行测试"""
        print_header(f"运行测试: {test_type}")

        test_scripts = {
            "quick": "tests/quick_verify.py",
            "full": "tests/automated_test.py",
        }

        if test_type not in test_scripts:
            print_error(f"未知的测试类型: {test_type}")
            return False

        script = test_scripts[test_type]
        script_path = self.base_dir / script

        if not script_path.exists():
            print_error(f"测试脚本不存在: {script}")
            return False

        try:
            # 快速测试不需要参数
            cmd = [sys.executable, str(script_path)]

            # 完整测试添加 --skip-slow 参数
            if test_type == "full":
                cmd.append("--skip-slow")

            print_info(f"运行: {' '.join(cmd)}")

            result = subprocess.run(cmd, cwd=str(self.base_dir))

            return result.returncode == 0

        except Exception as e:
            print_error(f"运行测试失败: {e}")
            return False

    def open_browser(self):
        """打开浏览器"""
        print_header("打开浏览器")

        import webbrowser

        urls = [
            ("主页", f"{self.base_url}"),
            ("新 API", f"{self.base_url}?use_new_api=true"),
            ("旧 API", f"{self.base_url}?use_new_api=false"),
        ]

        for name, url in urls:
            print_info(f"{name}: {url}")
            webbrowser.open(url)

        print_success("已在浏览器中打开测试页面")

    def stop_server(self):
        """停止服务器"""
        if self.server_process:
            print_info("停止服务器...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            print_success("服务器已停止")

    def run_all(self, test_type: str = "quick", open_browser: bool = False):
        """运行完整流程"""
        try:
            print_header("OpenCode 自动化测试")
            print_info(f"项目目录: {self.base_dir}")
            print_info(f"服务地址: {self.base_url}")

            # 1. 停止旧服务
            self.stop_all_servers()

            # 2. 启动新服务
            if not self.start_server():
                return False

            # 3. 运行测试
            if test_type:
                success = self.run_test(test_type)
                if not success:
                    print_error("测试失败")

            # 4. 打开浏览器（可选）
            if open_browser:
                self.open_browser()

            print_header("测试完成")
            print_info("服务器仍在运行")
            print_info("按 Ctrl+C 停止服务器")

            # 保持服务器运行
            try:
                self.server_process.wait()
            except KeyboardInterrupt:
                print("\n")
                print_info("收到中断信号")
                self.stop_server()

            return True

        except Exception as e:
            print_error(f"运行失败: {e}")
            return False
        finally:
            # 清理
            if self.server_process and self.server_process.poll() is None:
                self.stop_server()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenCode 服务器管理器")
    parser.add_argument(
        "--test", "-t",
        choices=["quick", "full", "none"],
        default="quick",
        help="测试类型（默认: quick）"
    )
    parser.add_argument(
        "--browser", "-b",
        action="store_true",
        help="打开浏览器"
    )
    parser.add_argument(
        "--base-dir",
        help="项目根目录"
    )

    args = parser.parse_args()

    manager = ServerManager(base_dir=args.base_dir)

    test_type = args.test if args.test != "none" else None
    success = manager.run_all(test_type=test_type, open_browser=args.browser)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
