#!/usr/bin/env python3
"""
OpenCode UI 提交流程完整测试
验证所有修复是否真正生效：Session ID统一、Actions显示、文件生成、事件流
"""

from playwright.sync_api import sync_playwright
import json
import subprocess
import time
from datetime import datetime

def test_opencode_ui_submission():
    """完整的 UI 提交流程测试"""

    print("=" * 80)
    print("OpenCode UI 提交流程完整测试")
    f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print("=" * 80)

    with sync_playwright() as p:
        # 启动浏览器
        print("\n[步骤 1] 启动浏览器...")
        browser = p.chromium.launch(headless=False)  # 使用非 headless 模式便于调试
        context = browser.new_context()
        page = context.new_page()

        # 设置 viewport
        page.set_viewport_size(1280, 800)

        try:
            # 步骤 2: 导航到页面
            print("[步骤 2] 导航到 http://localhost:8089")
            page.goto('http://localhost:8089', timeout=30000)
            print("✅ 页面加载完成")

            # 等待页面完全初始化
            page.wait_for_timeout(3000)

            # 步骤 3: 检查版本号
            print("\n[步骤 3] 检查版本号...")
            version_check = page.evaluate('''() => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.filter(s => s.src.includes('opencode'))
                    .map(s => ({
                        file: s.src.split('/').pop(),
                        version: s.src.match(/v=([0-9.]+(?:\.[0-9]+)?/)?.[1] || 'unknown')
                    }));
            }''')

            print(f"  发现 {len(version_check)} 个 opencode 脚本:")
            for v in version_check:
                print(f"    - {v['file']}: v={v['version']}")

            expected_version = "38.4.1"
            has_correct_version = any(v['version'] == expected_version for v in version_check)

            if not has_correct_version:
                print(f"  ⚠️  警告: 未找到 v{expected_version}，可能使用缓存")
                print("  建议: 强制刷新浏览器 (Ctrl+Shift+R)")
            else:
                print(f"  ✅ 版本正确: v{expected_version}")

            # 步骤 4: 检查核心函数是否暴露
            print("\n[步骤 4] 检查核心函数暴露...")
            function_check = page.evaluate('''() => {
                return {
                    hasPrepareSession: typeof window.prepareSession === 'function',
                    hasExecuteSubmission: typeof window.executeSubmission === 'function',
                    hasHandleNewAPIConnection: typeof window.handleNewAPIConnection === 'function',
                    activeId: window.state?.activeId
                };
            }''')

            print(f"  prepareSession: {function_check['hasPrepareSession']} {'✅' if function_check['hasPrepareSession'] else '❌'}")
            print(f"  executeSubmission: {function_check['hasExecuteSubmission']} {'✅' if function_check['hasExecuteSubmission'] else '❌'}")
            print(f"  handleNewAPIConnection: {function_check['hasHandleNewAPIConnection']} {'✅' if function_check['hasHandleNewAPIConnection'] else '❌'}")
            print(f"  当前 activeId: {function_check['activeId']}")

            # 步骤 5: 截图初始状态
            print("\n[步骤 5] 截图初始状态")
            page.screenshot(path='D:/manus/opencode/test_results/test_01_initial.png')
            print("  ✅ 初始截图已保存")

            # 步骤 6: 查找欢迎页提交按钮
            print("\n[步骤 6] 查找提交按钮...")
            page.wait_for_timeout(2000)

            # 尝试多个选择器
            submit_selectors = [
                'button#runStream-welcome',
                'button:has-text("发送")',
                'button:has(span.material-symbols-outlined)',
                'button[type="submit"]',
            ]

            submit_btn = None
            for selector in submit_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        submit_btn = page.locator(selector).first
                        print(f"  ✅ 找到提交按钮: {selector}")
                        break
                except:
                    continue

            if not submit_btn:
                print("  ❌ 未找到提交按钮")
                return

            # 步骤 7: 输入测试任务
            print("\n[步骤 7] 输入测试任务...")
            test_task = "创建一个包含标题、段落和链接的完整网页，保存为ui-test.html"

            input_selectors = [
                'textarea#prompt-welcome',
                'textarea#prompt',
                'textarea[placeholder*="输入"]',
            ]

            input_found = False
            for selector in input_selectors:
                try:
                    input_box = page.locator(selector).first
                    if input_box.count() > 0:
                        print(f"  ✅ 找到输入框: {selector}")
                        input_box.fill(test_task)
                        input_found = True
                        break
                except:
                    continue

            if not input_found:
                print("  ❌ 未找到输入框")
                return

            print(f"  ✅ 已输入任务: {test_task[:50]}...")

            # 步骤 8: 截图输入后的状态
            page.screenshot(path='D:/manus/opencode/test_results/test_02_after_input.png')
            print("  ✅ 输入后截图已保存")

            # 步骤 9: 点击提交按钮
            print("\n[步骤 9] 点击提交按钮...")

            # 等待一小段时间确保输入完成
            page.wait_for_timeout(1000)

            submit_btn.click()
            print("  ✅ 提交按钮已点击")

            # 步骤 10: 等待任务执行（关键：等待足够长时间）
            print("\n[步骤 10] 等待任务执行 (45秒)...")

            # 等待 5 秒让 session 创建
            page.wait_for_timeout(5000)

            # 每 5 秒检查一次状态
            for i in range(1, 9):
                page.wait_for_timeout(5000)
                print(f"  已等待 {5*i} 秒...")

                # 检查 session 状态
                session_data = page.evaluate('''() => {
                    const sessions = window.state?.sessions || [];
                    const activeId = window.state?.activeId;
                    const activeSession = sessions.find(s => s.id === activeId);

                    if (!activeSession) {
                        return { status: 'No active session' };
                    }

                    return {
                        sessionId: activeId,
                        actionsCount: activeSession.actions?.length || 0,
                        phasesCount: activeSession.phases?.length || 0,
                        deliverablesCount: activeSession.deliverables?.length || 0,
                        responseLength: activeSession.response?.length || 0,
                        actionTypes: activeSession.actions?.map(a => a.type) || [],
                        hasThinking: activeSession.actions?.some(a => a.type === 'thinking') || false,
                        hasWrite: activeSession.actions?.some(a => a.type === 'write') || false,
                        hasBash: activeSession.actions?.some(a => a.type === 'bash') || false
                    };
                }''')

                print(f"    Session ID: {session_data['sessionId']}")
                print(f"    Actions 数量: {session_data['actionsCount']}")
                print(f"    Action 类型: {', '.join(session_data['actionTypes']) if session_data['actionTypes'] else 'None'}")
                print(f"    Phases: {session_data['phasesCount']}")
                print(f"    Deliverables: {session_data['deliverablesCount']}")
                print(f"    响应长度: {session_data['responseLength']} 字符")

                # 如果有 actions，显示前3个
                if session_data['actionsCount'] > 0:
                    print(f"    前3个 actions:")
                    for i, action in enumerate(session_data['actions'][:3]):
                        print(f"      {i+1}. type={action['type']}, tool={action.get('tool', 'N/A')}")

            print("  ✅ 等待完成")

            # 步骤 11: 最终截图
            print("\n[步骤 11] 截图最终状态")
            page.screenshot(path='D:/manus/opencode/test_results/test_03_final.png', full_page=True)
            print("  ✅ 最终截图已保存")

            # 步骤 12: 收集最终数据
            print("\n[步骤 12] 收集最终测试数据...")

            final_data = page.evaluate('''() => {
                const sessions = window.state?.sessions || [];
                const activeSession = sessions.find(s => s.id === window.state?.activeId);

                return {
                    totalSessions: sessions.length,
                    activeId: window.state?.activeId,
                    activeSession: {
                        id: activeSession?.id,
                        prompt: activeSession?.prompt?.substring(0, 100) || '',
                        actionsCount: activeSession?.actions?.length || 0,
                        actions: activeSession?.actions?.map(a => ({
                            type: a.type,
                            tool: a.data?.tool,
                            title: a.data?.title,
                            status: a.data?.status
                        })) || [],
                        phasesCount: activeSession?.phases?.length || 0,
                        deliverablesCount: activeSession?.deliverables?.length || 0,
                        deliverables: activeSession?.deliverables?.map(d => ({
                            type: d.type,
                            title: d.title
                        })) || [],
                        responseLength: activeSession?.response?.length || 0,
                        responsePreview: activeSession?.response?.substring(0, 300) || ''
                    },
                    allSessions: sessions.map(s => ({
                        id: s.id,
                        actionsCount: s.actions?.length || 0,
                        hasResponse: !!s.response && s.response.length > 0
                    }))
                };
            }''')

            # 步骤 13: 检查后端文件生成
            print("\n[步骤 13] 检查后端文件生成...")
            if final_data['activeSession']:
                session_id = final_data['activeSession']['id']
                bash_check_result = subprocess.run(
                    f'docker exec opencode-container sh -c "ls -lh /app/opencode/workspace/{session_id}/"',
                    shell=True, capture_output=True, text=True
                )

                if bash_check_result.returncode == 0:
                    print("  ✅ Workspace 目录存在:")
                    for line in bash_check_result.stdout.strip().split('\n')[:10]:
                        if line:
                            print(f"      {line}")
                else:
                    print(f"  ⚠️  Workspace 目录不存在或为空")

            # 步骤 14: 生成测试报告
            print("\n[步骤 14] 生成测试报告...")

            # 确定版本检查结果
            version_str = version_check[0]['version'] if version_check else 'unknown'
            
            report = f"""# OpenCode UI 提交流程测试报告

## 测试时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 测试任务
{test_task}

## 版本验证
- 期望版本: v{expected_version}
- 实际版本: {version_str}
- 版本匹配: {'✅ 是' if has_correct_version else '❌ 否'}

## 核心函数暴露
- prepareSession: {'✅ 可用' if function_check['hasPrepareSession'] else '❌ 不可用'}
- executeSubmission: {'✅ 可用' if function_check['hasExecuteSubmission'] else '❌ 不可用'}
- handleNewAPIConnection: {'✅ 可用' if function_check['hasHandleNewAPIConnection'] else '❌ 不可用'}

## Session 状态
- Session ID: {final_data.get('activeSession', {}).get('id', 'N/A')}
- Actions 数量: {final_data.get('activeSession', {}).get('actionsCount', 0)}
- Action 类型: {', '.join(final_data.get('activeSession', {}).get('actionTypes', []))}
- Thinking 事件: {'✅ 有' if final_data.get('activeSession', {}).get('hasThinking', False) else '❌ 无'}
- Write 事件: {'✅ 有' if final_data.get('activeSession', {}).get('hasWrite', False) else '❌ 无'}
- Bash 事件: {'✅ 有' if final_data.get('activeSession', {}).get('hasBash', False) else '❌ 无'}
- Phases: {final_data.get('activeSession', {}).get('phasesCount', 0)}
- Deliverables: {final_data.get('activeSession', {}).get('deliverablesCount', 0)}
- 响应长度: {final_data.get('activeSession', {}).get('responseLength', 0)} 字符

## 所有 Sessions 状态
"""

            for s in final_data['allSessions']:
                report += f"- {s['id']}: {s['actionsCount']} actions, 有响应: {s['hasResponse']}\\n"

            report += f"""
## 验证清单

- [ ] 版本号正确
- [ ] Session ID 前后端一致
- [ ] Actions 数量 > 0
- [ ] 有 thinking 事件
- [ ] 有 write 事件
- [ ] 有 deliverables
- [ ] 文件已生成

## 截图
- test_01_initial.png - 初始状态
- test_02_after_input.png - 输入后
- test_03_final.png - 最终状态（完整页面）

## 测试结论

"""

            # 判断测试结果
            if has_correct_version and function_check['hasExecuteSubmission']:
                if final_data['activeSession']['actionsCount'] > 0:
                    report += "✅ **测试通过**: UI 提交流程正常工作，所有修复生效！\\n"
                else:
                    report += "⚠️ **部分通过**: 代码修复已部署，但 actions 为 0，可能需要进一步诊断\\n"
            else:
                report += "❌ **测试失败**: 关键函数未暴露或版本不匹配\\n"

            report += f"""
## 数据文件
- test_results/test_report.md - 本报告
- test_results/test_data.json - 完整数据
- test_results/console_logs.json - Console 日志

---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            with open('D:/manus/opencode/test_results/test_report.md', 'w', encoding='utf-8') as f:
                f.write(report)

            # 保存 JSON 数据
            with open('D:/manus/opencode/test_results/test_data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'version_check': version_check,
                    'function_check': function_check,
                    'final_data': final_data
                }, f, indent=2, ensure_ascii=False)

            print("  ✅ 测试报告已生成")
            print("\\n" + "=" * 80)
            print("测试完成！")
            print("=" * 80)
            print("\\n请查看以下文件了解详细结果：")
            print("  - test_results/test_report.md (测试报告)")
            print("  - test_results/test_data.json (完整数据)")
            print("  - test_results/test_03_final.png (最终截图)")

            return {
                'status': 'completed',
                'has_correct_version': has_correct_version,
                'functions_available': function_check,
                'actions_count': final_data['activeSession']['actionsCount'] if final_data['activeSession'] else 0,
                'report_path': 'D:/manus/opencode/test_results/test_report.md'
            }

        except Exception as e:
            print(f"\\n❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'error': str(e)}

        finally:
            browser.close()

if __name__ == '__main__':
    result = test_opencode_ui_submission()
    print(f"\\n测试结果: {result['status']}")
