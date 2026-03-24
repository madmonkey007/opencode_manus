#!/usr/bin/env python
"""
快速验证后端API返回的数据结构

用法：
    python verify_api.py [session_id]

示例：
    python verify_api.py ses_2730c2ed
"""

import requests
import json
import sys

def verify_session_api(session_id):
    """验证session API返回的数据结构"""

    url = f"http://localhost:8089/opencode/session/{session_id}/messages"

    print(f"📡 正在请求: {url}")
    print("-" * 60)

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        print(f"✅ 请求成功 (Status: {response.status_code})")
        print()

        # 分析数据结构
        print("📊 数据分析:")
        print("-" * 60)

        session_id_returned = data.get("session_id")
        messages = data.get("messages", [])
        phases = data.get("phases", [])
        count = data.get("count", 0)

        print(f"Session ID: {session_id_returned}")
        print(f"消息数量: {count}")
        print(f"Phase数量: {len(phases)}")
        print()

        # 分析每个message的parts
        for i, msg in enumerate(messages, 1):
            info = msg.get("info", {})
            parts = msg.get("parts", [])

            print(f"📨 Message {i}:")
            print(f"   ID: {info.get('id')}")
            print(f"   Role: {info.get('role')}")
            print(f"   Parts数量: {len(parts)}")
            print()

            # 统计part类型
            part_types = {}
            for part in parts:
                part_type = part.get("type", "unknown")
                if part_type not in part_types:
                    part_types[part_type] = 0
                part_types[part_type] += 1

            print(f"   Part类型分布:")
            for part_type, count in part_types.items():
                print(f"     - {part_type}: {count}个")

            # 显示前3个part的详细信息
            print()
            print(f"   前3个Part详情:")
            for j, part in enumerate(parts[:3], 1):
                part_type = part.get("type")
                content = part.get("content", {})
                text = content.get("text", "")

                print(f"     Part {j} ({part_type}):")
                if text:
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"       内容: {preview}")
                else:
                    print(f"       内容: (空)")

                if part_type == "tool":
                    tool = content.get("tool")
                    print(f"       工具: {tool}")

            print()

        # 保存完整JSON到文件
        output_file = f"api_output_{session_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("-" * 60)
        print(f"✅ 完整JSON已保存到: {output_file}")
        print()

        # 问题检查
        print("🔍 问题检查:")
        print("-" * 60)

        has_thought = False
        has_text = False
        has_tool = False

        for msg in messages:
            for part in msg.get("parts", []):
                part_type = part.get("type")
                if part_type == "thought":
                    has_thought = True
                elif part_type == "text":
                    has_text = True
                elif part_type == "tool":
                    has_tool = True

        print(f"✅ 包含thought: {'是' if has_thought else '否'}")
        print(f"✅ 包含text: {'是' if has_text else '否'}")
        print(f"✅ 包含tool: {'是' if has_tool else '否'}")
        print(f"✅ 包含phases: {'是' if phases else '否'}")
        print()

        if not has_thought and count > 0:
            print("⚠️  警告: 没有发现thought类型的parts")

        if not has_text and count > 0:
            print("⚠️  警告: 没有发现text类型的parts")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 请提供session ID")
        print()
        print("用法:")
        print("  python verify_api.py <session_id>")
        print()
        print("示例:")
        print("  python verify_api.py ses_2730c2ed")
        sys.exit(1)

    session_id = sys.argv[1]
    success = verify_session_api(session_id)

    sys.exit(0 if success else 1)
