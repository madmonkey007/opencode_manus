#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话创建诊断脚本 - 快速定位问题
"""
import asyncio
import os
import uuid
import subprocess
import sys

async def test_session_creation():
    """测试会话创建的各个环节"""

    print("="*70)
    print("会话创建诊断 - 快速定位问题")
    print("="*70)

    # 测试1: 基本目录权限
    print("\n[测试1] 基本目录创建权限...")

    test_dir = "test_session_" + uuid.uuid4().hex[:8]
    try:
        os.makedirs(test_dir, exist_ok=True)
        print(f"  ✓ 可创建目录: {test_dir}")
        os.rmdir(test_dir)
        print(f"  ✓ 可删除目录")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return

    # 测试2: UUID生成
    print("\n[测试2] UUID生成...")
    try:
        session_id = f"ses_{uuid.uuid4().hex}"
        print(f"  ✓ Session ID: {session_id}")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return

    # 测试3: Workspace目录权限
    print("\n[测试3] Workspace目录权限...")
    workspace_base = "workspace"
    try:
        if not os.path.exists(workspace_base):
            os.makedirs(workspace_base)
        print(f"  ✓ Workspace目录可访问: {workspace_base}")

        # 创建测试session目录
        session_dir = os.path.join(workspace_base, session_id)
        os.makedirs(session_dir, exist_ok=True)
        print(f"  ✓ 可创建session目录: {session_dir}")

        # 创建测试文件
        test_file = os.path.join(session_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        print(f"  ✓ 可创建文件: {test_file}")

        # 清理
        os.remove(test_file)
        os.rmdir(session_dir)
        print(f"  ✓ 清理完成")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return

    # 测试4: API创建会话
    print("\n[测试4] API创建会话...")
    try:
        import requests

        # 先创建会话
        response = requests.post(
            "http://localhost:8089/opencode/session",
            headers={'Content-Type': 'application/json'},
            json={'title': '诊断测试', 'mode': 'build'},
            timeout=10
        )

        if response.status_code == 200:
            session = response.json()
            api_session_id = session.get('id')
            print(f"  ✓ API创建成功: {api_session_id}")

            # 检查workspace是否创建了目录
            api_session_dir = os.path.join(workspace_base, api_session_id)
            if os.path.exists(api_session_dir):
                print(f"  ✓ Workspace目录已创建: {api_session_dir}")
                files = os.listdir(api_session_dir)
                print(f"     包含文件: {files}")
            else:
                print(f"  ✗ Workspace目录未创建: {api_session_dir}")

        else:
            print(f"  ✗ API创建失败: {response.status_code}")
            print(f"     响应: {response.text[:200]}")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    # 测试5: opencode CLI文件创建
    print("\n[测试5] opencode CLI文件创建...")

    # 检查是否使用config_host配置
    config_host_exists = os.path.exists("config_host/opencode.json")
    print(f"  config_host/opencode.json存在: {config_host_exists}")

    # 在现有session中测试
    workspace_dirs = [d for d in os.listdir("workspace") if os.path.isdir(os.path.join("workspace", d))]
    if workspace_dirs:
        test_session = workspace_dirs[0]
        print(f"  使用现有session测试: {test_session}")

        test_file = "cli_test.txt"
        cmd = f'cd workspace/{test_session} && opencode run --model new-api/gemini-3-flash-preview "创建{test_file}文件"'

        print(f"  执行命令: opencode run创建文件...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            print(f"   返回码: {result.returncode}")

            # 显示输出
            if result.stdout:
                print(f"  标准输出:")
                for line in result.stdout.split('\n')[:10]:
                    if line.strip():
                        print(f"    {line}")

            # 检查文件是否创建
            test_file_path = os.path.join("workspace", test_session, test_file)
            if os.path.exists(test_file_path):
                print(f"  ✓ 文件已创建: {test_file_path}")
                with open(test_file_path, 'r') as f:
                    content = f.read()
                print(f"     内容: {content[:100]}")
            else:
                print(f"  ✗ 文件未创建: {test_file_path}")

        except subprocess.TimeoutExpired:
            print("  ✗ 命令执行超时（30秒）")
        except Exception as e:
            print(f"  ✗ 错误: {e}")

    print("\n" + "="*70)
    print("诊断完成")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_session_creation())
