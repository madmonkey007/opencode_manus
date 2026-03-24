#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点选择器的单选功能
"""
import requests
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("API端点选择器单选功能测试")
print("=" * 80)

try:
    # 获取主页HTML
    resp = requests.get("http://127.0.0.1:8089/")
    html = resp.text

    # 检查按钮是否存在
    has_web_btn = "api-web-btn" in html
    has_cli_btn = "api-cli-btn" in html

    # 检查是否有硬编码样式（应该没有）
    web_btn_section = html[html.find('api-web-btn'):html.find('api-web-btn')+500]
    cli_btn_section = html[html.find('api-cli-btn'):html.find('api-cli-btn')+500]

    # 硬编码的选中样式类（不应该出现）
    hardcoded_selected = 'bg-white dark:bg-gray-700 shadow' in web_btn_section

    # 检查JavaScript是否正确实现单选逻辑
    has_update_function = 'updateEndpointButtons' in html
    has_toggle_logic = 'webBtn.classList.remove' in html and 'cliBtn.classList.remove' in html

    print("\n✅ 按钮存在性检查:")
    print(f"  - Web按钮: {'✓' if has_web_btn else '✗'}")
    print(f"  - CLI按钮: {'✓' if has_cli_btn else '✗'}")

    print("\n✅ 样式配置检查:")
    print(f"  - 无硬编码选中样式: {'✓ (修复成功)' if not hardcoded_selected else '✗ (仍有硬编码)'}")

    print("\n✅ JavaScript逻辑检查:")
    print(f"  - updateEndpointButtons函数: {'✓' if has_update_function else '✗'}")
    print(f"  - 单选互斥逻辑: {'✓' if has_toggle_logic else '✗'}")

    print("\n" + "=" * 80)
    print("手动验证步骤:")
    print("=" * 80)
    print("\n1. 访问: http://127.0.0.1:8089")
    print("2. 观察主header右上角的 [Web] [CLI] 按钮")
    print("3. 默认状态: Web按钮应该是白色背景+阴影（选中），CLI是灰色（未选中）")
    print("4. 点击CLI按钮:")
    print("   - CLI按钮变为白色背景+阴影（选中）")
    print("   - Web按钮变为灰色（未选中）")
    print("5. 点击Web按钮:")
    print("   - Web按钮恢复白色背景+阴影（选中）")
    print("   - CLI按钮恢复灰色（未选中）")
    print("\n✓ 这是正确的单选行为")
    print("=" * 80)

    if has_web_btn and has_cli_btn and not hardcoded_selected and has_toggle_logic:
        print("\n[SUCCESS] 所有检查通过！API端点选择器单选功能已修复 ✓")
    else:
        print("\n[WARNING] 部分检查未通过，可能需要进一步调试")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    print("请确保Docker容器正在运行: docker ps")
