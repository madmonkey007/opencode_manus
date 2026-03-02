#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版API测试 - 直接测试历史数据修复
"""
import requests
import sqlite3
import json

def test_api_endpoints():
    """直接测试API端点"""
    print("=" * 60)
    print("测试历史数据API端点")
    print("=" * 60)

    base_url = "http://localhost:8089"

    # 步骤1：从数据库获取测试会话ID
    print("\n[步骤1] 从数据库获取测试会话...")
    try:
        conn = sqlite3.connect('D:/manus/opencode/history.db')
        cursor = conn.cursor()

        # 查找一个有messages和steps的会话
        cursor.execute("""
            SELECT DISTINCT m.session_id,
                (SELECT COUNT(*) FROM messages WHERE session_id = m.session_id) as msg_count,
                (SELECT COUNT(*) FROM steps WHERE session_id = m.session_id) as step_count
            FROM messages m
            WHERE EXISTS (SELECT 1 FROM steps s WHERE s.session_id = m.session_id)
            LIMIT 1
        """)

        result = cursor.fetchone()
        conn.close()

        if not result:
            print("未找到同时有messages和steps的会话，使用任意会话...")
            conn = sqlite3.connect('D:/manus/opencode/history.db')
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions LIMIT 1")
            result = cursor.fetchone()
            conn.close()

        if result:
            session_id = result[0]
            print(f"测试会话ID: {session_id}")
        else:
            print("数据库中没有会话数据")
            return
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return

    # 步骤2：测试messages API
    print(f"\n[步骤2] 测试Messages API...")
    messages_url = f"{base_url}/opencode/session/{session_id}/messages"
    print(f"URL: {messages_url}")

    try:
        response = requests.get(messages_url, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            messages = data.get('messages', [])

            print(f"返回消息数量: {count}")

            if count > 0:
                print("\n消息列表:")
                for i, msg in enumerate(messages[:5], 1):
                    info = msg.get('info', {})
                    role = info.get('role', 'unknown')
                    msg_id = info.get('id', 'N/A')
                    print(f"  {i}. {msg_id} ({role})")

                if count > 5:
                    print(f"  ... 还有 {count - 5} 条消息")

                print("\n✅ Messages API 测试成功 - 数据恢复功能正常！")
            else:
                print("\n⚠ Messages API 返回空列表")
        else:
            print(f"✗ API调用失败: {response.text}")
    except Exception as e:
        print(f"✗ Messages API 测试失败: {e}")

    # 步骤3：测试timeline API
    print(f"\n[步骤3] 测试Timeline API...")
    timeline_url = f"{base_url}/opencode/session/{session_id}/timeline"
    print(f"URL: {timeline_url}")

    try:
        response = requests.get(timeline_url, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            timeline = data.get('timeline', [])

            print(f"返回事件数量: {count}")

            if count > 0:
                print("\n时间轴事件:")
                for i, event in enumerate(timeline[:10], 1):
                    action = event.get('action', 'unknown')
                    path = event.get('path', '')
                    timestamp = event.get('timestamp', 0)
                    print(f"  {i}. [{action}] {path or '(无路径)'}")

                if count > 10:
                    print(f"  ... 还有 {count - 10} 个事件")

                print("\n✅ Timeline API 测试成功 - 工具调用事件恢复正常！")
            else:
                print("\n⚠ Timeline API 返回空列表 (该会话可能没有工具调用)")
        else:
            print(f"✗ API调用失败: {response.text}")
    except Exception as e:
        print(f"✗ Timeline API 测试失败: {e}")

    # 步骤4：验证数据库与API一致性
    print(f"\n[步骤4] 验证数据一致性...")
    try:
        conn = sqlite3.connect('D:/manus/opencode/history.db')
        cursor = conn.cursor()

        # 检查数据库中的记录数
        cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
        db_msg_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM steps WHERE session_id = ?", (session_id,))
        db_step_count = cursor.fetchone()[0]

        conn.close()

        print(f"数据库中messages数量: {db_msg_count}")
        print(f"数据库中steps数量: {db_step_count}")

        # 再次调用API获取实际返回数量
        msg_response = requests.get(messages_url, timeout=10)
        api_msg_count = msg_response.json().get('count', 0)

        timeline_response = requests.get(timeline_url, timeout=10)
        api_step_count = timeline_response.json().get('count', 0)

        print(f"API返回messages数量: {api_msg_count}")
        print(f"API返回steps数量: {api_step_count}")

        if api_msg_count == db_msg_count:
            print("\n✅ Messages数据一致性验证通过")
        else:
            print(f"\n⚠ Messages数量不匹配: 数据库{db_msg_count} vs API{api_msg_count}")

        if api_step_count == db_step_count:
            print("✅ Steps数据一致性验证通过")
        else:
            print(f"⚠ Steps数量不匹配: 数据库{db_step_count} vs API{api_step_count}")

    except Exception as e:
        print(f"数据一致性验证失败: {e}")

    print("\n" + "=" * 60)
    print("API测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_api_endpoints()
