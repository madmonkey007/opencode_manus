#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断历史记录中的重复事件
"""
import requests
import json
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("历史记录重复事件诊断")
print("=" * 80)

try:
    # 获取所有session
    resp = requests.get("http://127.0.0.1:8089/opencode/sessions")
    if resp.status_code != 200:
        print(f"[ERROR] Failed to get sessions: {resp.status_code}")
        sys.exit(1)

    sessions = resp.json()
    print(f"\n找到 {len(sessions)} 个session\n")

    duplicate_count = 0
    total_issues = 0

    for session in sessions:
        session_id = session.get('id')
        title = session.get('title', 'No title')[:50]

        print(f"\n{'='*80}")
        print(f"Session: {session_id}")
        print(f"Title: {title}")
        print(f"{'='*80}")

        # 检查phases中的events
        phases = session.get('phases', [])
        if phases:
            for phase in phases:
                phase_id = phase.get('id')
                events = phase.get('events', [])

                # 检查phase.events中的重复thought
                thought_events = [e for e in events if e.get('type') == 'thought']
                if thought_events:
                    print(f"\n  Phase {phase_id}:")
                    print(f"    - 总事件数: {len(events)}")
                    print(f"    - Thought事件数: {len(thought_events)}")

                    # 检查内容重复
                    seen_contents = {}
                    duplicates = []
                    for i, thought in enumerate(thought_events):
                        content = thought.get('content', '')[:100]
                        if content in seen_contents:
                            duplicates.append({
                                'index': i,
                                'content': content,
                                'first_index': seen_contents[content]
                            })
                            duplicate_count += 1
                        else:
                            seen_contents[content] = i

                    if duplicates:
                        total_issues += 1
                        print(f"    ⚠️  发现 {len(duplicates)} 个重复的thought事件:")
                        for dup in duplicates[:3]:  # 只显示前3个
                            print(f"       - 位置{dup['index']} (首次出现在位置{dup['first_index']}): {dup['content']}...")

                # 检查phase.events中的重复action
                action_events = [e for e in events if e.get('type') == 'action']
                if action_events:
                    print(f"    - Action事件数: {len(action_events)}")

                    # 检查ID重复
                    seen_ids = {}
                    duplicates = []
                    for i, action in enumerate(action_events):
                        action_id = action.get('id')
                        if action_id in seen_ids:
                            duplicates.append({
                                'index': i,
                                'id': action_id,
                                'first_index': seen_ids[action_id]
                            })
                            duplicate_count += 1
                        else:
                            seen_ids[action_id] = i

                    if duplicates:
                        total_issues += 1
                        print(f"    ⚠️  发现 {len(duplicates)} 个重复的action事件:")
                        for dup in duplicates[:3]:
                            print(f"       - 位置{dup['index']} (ID: {dup['id']}, 首次出现在位置{dup['first_index']})")

        # 检查orphanEvents中的重复
        orphan_events = session.get('orphanEvents', [])
        if orphan_events:
            print(f"\n  orphanEvents: {len(orphan_events)} 个事件")

            # 按类型分组
            by_type = {}
            for event in orphan_events:
                etype = event.get('type', 'unknown')
                if etype not in by_type:
                    by_type[etype] = []
                by_type[etype].append(event)

            for etype, events in by_type.items():
                print(f"    - {etype}: {len(events)}")

    print(f"\n{'='*80}")
    print(f"诊断总结")
    print(f"{'='*80}")
    print(f"  - 总session数: {len(sessions)}")
    print(f"  - 发现问题的session数: {total_issues}")
    print(f"  - 重复事件总数: {duplicate_count}")

    if duplicate_count > 0:
        print(f"\n⚠️  发现重复事件！")
        print(f"\n可能原因:")
        print(f"  1. 同一个事件被添加到多个数组（actions + orphanEvents + phase.events）")
        print(f"  2. loadState()合并localStorage和后端数据时未去重")
        print(f"  3. SSE事件处理时重复添加")
        print(f"\n建议修复方案:")
        print(f"  1. 移除第2526行的 s.orphanEvents.push(actionEvent)")
        print(f"  2. 或添加事件去重逻辑（基于唯一ID）")
        print(f"  3. 统一事件存储位置，避免多重引用")
    else:
        print(f"\n✓ 未发现重复事件")

    print(f"{'='*80}")

except Exception as e:
    print(f"\n[ERROR] 诊断失败: {e}")
    import traceback
    traceback.print_exc()
