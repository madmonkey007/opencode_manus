#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的 OpenCode 功能测试
测试 SSE 连接、事件流、工具调用和文件生成
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime
import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_opencode_full_workflow():
    """完整测试 OpenCode 工作流"""

    print("=" * 80)
    print("OpenCode 完整功能测试")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 收集 console 日志
        console_logs = []
        def handle_console(msg):
            try:
                # 移除 emoji 和特殊字符，避免编码错误
                text_clean = msg.text.encode('ascii', errors='ignore').decode('ascii')
                log_entry = {
                    'type': msg.type,
                    'text': msg.text,
                    'timestamp': datetime.now().isoformat()
                }
                console_logs.append(log_entry)
                print(f"[Console {msg.type}] {text_clean[:80]}")
            except Exception as e:
                # 忽略编码错误，继续收集日志
                pass

        page.on('console', handle_console)

        try:
            # 步骤 1: 导航到页面
            print("\n[步骤 1] 导航到 http://localhost:8089")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            print("✅ 页面加载完成")

            # 步骤 2: 等待页面完全初始化
            print("\n[步骤 2] 等待页面初始化")
            page.wait_for_timeout(2000)
            print("✅ 页面初始化完成")

            # 步骤 3: 截图初始状态
            print("\n[步骤 3] 截图初始状态")
            page.screenshot(path='D:/manus/opencode/test_results/01_initial.png')
            print("✅ 初始截图已保存")

            # 步骤 4: 检查版本号
            print("\n[步骤 4] 检查版本号")
            version_logs = [log for log in console_logs if 'v=38.3' in log['text']]
            print(f"发现 {len(version_logs)} 条版本日志")
            for log in version_logs[:3]:
                print(f"  - {log['text'][:80]}")

            # 步骤 5: 输入测试任务
            print("\n[步骤 5] 输入测试任务")
            test_prompt = "创建一个简单的hello world网页，保存为hello.html"
            print(f"测试提示词: {test_prompt}")

            # 尝试多种选择器定位输入框
            input_selectors = [
                'textarea[id="prompt"]',
                'textarea[id="prompt-welcome"]',
                'textarea[placeholder*="输入"]',
                'textarea',
            ]

            input_found = False
            for selector in input_selectors:
                try:
                    input_box = page.locator(selector).first
                    if input_box.count() > 0:
                        print(f"✅ 找到输入框: {selector}")
                        input_box.fill(test_prompt)
                        input_found = True
                        break
                except Exception as e:
                    continue

            if not input_found:
                print("❌ 未找到输入框，尝试直接输入")
                page.keyboard.type(test_prompt)

            page.wait_for_timeout(1000)
            page.screenshot(path='D:/manus/opencode/test_results/02_after_input.png')
            print("✅ 文本已输入")

            # 步骤 6: 点击提交按钮
            print("\n[步骤 6] 点击提交按钮")
            submit_selectors = [
                'button:has-text("发送")',
                'button[id="runStream"]',
                'button:has([class*="arrow_upward"])',
                'button',
            ]

            clicked = False
            for selector in submit_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0:
                        print(f"✅ 找到提交按钮: {selector}")
                        btn.click()
                        clicked = True
                        break
                except Exception as e:
                    continue

            if not clicked:
                print("⚠️ 未找到提交按钮，尝试按 Enter 键")
                page.keyboard.press('Enter')

            page.screenshot(path='D:/manus/opencode/test_results/03_after_submit.png')
            print("✅ 提交完成")

            # 步骤 7: 等待任务执行（关键：等待足够长时间）
            print("\n[步骤 7] 等待任务执行 (60秒)...")
            print("这将等待 AI agent 执行工具调用和文件生成")

            # 等待 SSE 连接建立
            print("等待 SSE 连接...")
            page.wait_for_timeout(5000)

            # 检查连接状态
            connection_logs = [log for log in console_logs if 'SSE' in log['text'] or 'Connected' in log['text']]
            print(f"发现 {len(connection_logs)} 条连接日志")
            for log in connection_logs[:5]:
                print(f"  - {log['text'][:100]}")

            # 继续等待事件流
            print("等待事件流和工具调用...")
            for i in range(11):
                page.wait_for_timeout(5000)
                print(f"  已等待 {5*(i+1)} 秒...")

                # 检查是否有新事件
                current_logs = len(console_logs)
                print(f"  当前日志数: {current_logs}")

            print("✅ 等待完成")

            # 步骤 8: 最终截图
            print("\n[步骤 8] 截图最终状态")
            page.screenshot(path='D:/manus/opencode/test_results/04_final.png', full_page=True)
            print("✅ 最终截图已保存")

            # 步骤 9: 分析 session 状态
            print("\n[步骤 9] 分析 session 状态")
            session_data = page.evaluate('''() => {
                const sessions = window.state?.sessions || [];
                const activeSession = sessions.find(s => s.id === window.state?.activeId);

                return {
                    totalSessions: sessions.length,
                    activeId: window.state?.activeId,
                    activeSession: {
                        id: activeSession?.id,
                        prompt: activeSession?.prompt?.substring(0, 100),
                        responseLength: activeSession?.response?.length || 0,
                        actionsCount: activeSession?.actions?.length || 0,
                        phasesCount: activeSession?.phases?.length || 0,
                        orphanEventsCount: activeSession?.orphanEvents?.length || 0,
                        actionsSample: activeSession?.actions?.slice(0, 3) || [],
                        hasThinking: activeSession?.actions?.some(a => a.type === 'thinking'),
                        hasWrite: activeSession?.actions?.some(a => a.type === 'write'),
                        hasBash: activeSession?.actions?.some(a => a.type === 'bash'),
                        hasToolCall: activeSession?.actions?.some(a => a.type === 'tool_call')
                    }
                };
            }''')

            print(f"✅ Session 数据已获取")
            print(f"  - 总 Session 数: {session_data['totalSessions']}")
            print(f"  - 当前 Session ID: {session_data['activeId']}")
            print(f"  - 响应长度: {session_data['activeSession']['responseLength']} 字符")
            print(f"  - Actions 数量: {session_data['activeSession']['actionsCount']}")
            print(f"  - Phases 数量: {session_data['activeSession']['phasesCount']}")
            print(f"  - Orphan Events: {session_data['activeSession']['orphanEventsCount']}")
            print(f"  - 有 Thinking 事件: {session_data['activeSession']['hasThinking']}")
            print(f"  - 有 Write 事件: {session_data['activeSession']['hasWrite']}")
            print(f"  - 有 Bash 事件: {session_data['activeSession']['hasBash']}")
            print(f"  - 有 Tool Call 事件: {session_data['activeSession']['hasToolCall']}")

            # 步骤 10: 分析错误日志
            print("\n[步骤 10] 分析错误日志")
            error_logs = [log for log in console_logs if log['type'] in ['error', 'warning']]
            print(f"发现 {len(error_logs)} 条错误/警告日志")
            for log in error_logs[:10]:
                print(f"  - [{log['type']}] {log['text'][:120]}")

            # 步骤 11: 分析网络请求
            print("\n[步骤 11] 分析网络请求")
            # 注意：需要在页面加载前启用网络监控

            # 步骤 12: 保存结果
            print("\n[步骤 12] 保存测试结果")
            results = {
                'timestamp': datetime.now().isoformat(),
                'test_prompt': test_prompt,
                'session_data': session_data,
                'console_logs_count': len(console_logs),
                'error_logs_count': len(error_logs),
                'console_logs_sample': console_logs[:20],
                'error_logs_sample': error_logs[:10]
            }

            with open('D:/manus/opencode/test_results/test_results_full.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            with open('D:/manus/opencode/test_results/console_logs_full.json', 'w', encoding='utf-8') as f:
                json.dump(console_logs, f, indent=2, ensure_ascii=False)

            print("✅ 测试结果已保存")

            # 步骤 13: 生成测试报告
            print("\n[步骤 13] 生成测试报告")
            report = f"""# OpenCode 完整功能测试报告

## 测试时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试任务
{test_prompt}

## Session 状态
- Session ID: {session_data['activeId']}
- 响应长度: {session_data['activeSession']['responseLength']} 字符
- Actions 数量: {session_data['activeSession']['actionsCount']}
- Phases 数量: {session_data['activeSession']['phasesCount']}

## 事件统计
- Thinking 事件: {'✅ 有' if session_data['activeSession']['hasThinking'] else '❌ 无'}
- Write 事件: {'✅ 有' if session_data['activeSession']['hasWrite'] else '❌ 无'}
- Bash 事件: {'✅ 有' if session_data['activeSession']['hasBash'] else '❌ 无'}
- Tool Call 事件: {'✅ 有' if session_data['activeSession']['hasToolCall'] else '❌ 无'}

## Console 日志
- 总日志数: {len(console_logs)}
- 错误日志数: {len(error_logs)}

## 问题分析
"""

            if session_data['activeSession']['actionsCount'] == 0:
                report += "\n### ⚠️ 问题: Actions 数组为空\n\n"
                report += "**可能原因**:\n"
                report += "1. 后端没有发送事件流（只有最终响应）\n"
                report += "2. 前端事件处理逻辑有问题\n"
                report += "3. 事件没有正确保存到 session.actions\n\n"
                report += "**建议**:\n"
                report += "- 检查后端是否使用 dev 分支（有完整事件流）\n"
                report += "- 检查 event-adapter.js 的事件处理逻辑\n"

            if not session_data['activeSession']['hasWrite']:
                report += "\n### ⚠️ 问题: 没有 Write 事件\n\n"
                report += "说明后端没有执行文件写入工具调用\n\n"

            if len(error_logs) > 0:
                report += f"\n### ⚠️ 发现 {len(error_logs)} 条错误日志\n\n"
                for log in error_logs[:5]:
                    report += f"- {log['text'][:100]}\n"

            report += "\n## 结论\n\n"

            if session_data['activeSession']['actionsCount'] > 0:
                report += "✅ 测试通过：事件流正常工作\n"
            elif session_data['activeSession']['responseLength'] > 0:
                report += "⚠️ 部分通过：SSE 连接成功且有响应，但缺少事件流\n"
                report += "这表明当前运行的后端版本不支持完整的 agent 事件流\n"
            else:
                report += "❌ 测试失败：没有响应\n"

            with open('D:/manus/opencode/test_results/TEST_REPORT_FULL.md', 'w', encoding='utf-8') as f:
                f.write(report)

            print("✅ 测试报告已生成")

            # 最终总结
            print("\n" + "=" * 80)
            print("测试完成总结")
            print("=" * 80)
            print(f"Session ID: {session_data['activeId']}")
            print(f"Actions 数量: {session_data['activeSession']['actionsCount']}")
            print(f"响应长度: {session_data['activeSession']['responseLength']} 字符")
            print(f"错误日志: {len(error_logs)} 条")
            print("\n请查看以下文件了解详细结果：")
            print("  - test_results/TEST_REPORT_FULL.md (测试报告)")
            print("  - test_results/test_results_full.json (测试数据)")
            print("  - test_results/console_logs_full.json (完整日志)")
            print("  - test_results/04_final.png (最终截图)")

        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

if __name__ == '__main__':
    test_opencode_full_workflow()
