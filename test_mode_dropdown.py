#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模式选择器下拉菜单
"""
import requests
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("模式选择器下拉菜单验证")
print("=" * 80)

try:
    # 获取主页HTML
    resp = requests.get("http://127.0.0.1:8089/")
    html = resp.text

    # 检查是否存在下拉菜单
    has_select = '<select id="input-mode-selector"' in html

    # 检查select元素内部是否有图标（应该没有）
    if has_select and 'input-mode-selector' in html:
        select_start = html.find('<select id="input-mode-selector"')
        select_end = html.find('</select>', select_start)
        select_content = html[select_start:select_end]
        has_icons = 'material-symbols-outlined' in select_content
    else:
        has_icons = False

    # 检查默认值是否为build
    has_default_build = 'value="build" selected' in html

    # 检查选项列表
    has_plan_option = '<option value="plan"' in html
    has_build_option = '<option value="build"' in html
    has_auto_option = '<option value="auto"' in html

    # 检查JavaScript事件处理
    has_change_event = "addEventListener('change'" in html or "selector.addEventListener('change'" in html

    print("\n✅ HTML结构检查:")
    print(f"  1. 下拉菜单存在: {'✓' if has_select else '✗'}")
    print(f"  2. 默认值为Build: {'✓' if has_default_build else '✗'}")

    print("\n✅ 选项检查:")
    print(f"  1. Plan选项: {'✓' if has_plan_option else '✗'}")
    print(f"  2. Build选项: {'✓' if has_build_option else '✗'}")
    print(f"  3. Auto选项: {'✓' if has_auto_option else '✗'}")

    print("\n✅ 样式检查:")
    print(f"  1. 无图标: {'✓ (已移除)' if not has_icons else '✗ (仍有图标)'}")

    print("\n" + "=" * 80)
    print("手动验证步骤:")
    print("=" * 80)
    print("\n1. 访问: http://127.0.0.1:8089")
    print("2. 在输入框左侧底部找到模式选择下拉菜单")
    print("3. 验证默认显示: 'Build 开发' (选中状态)")
    print("4. 点击下拉菜单，应该看到三个选项:")
    print("   - Plan 分析")
    print("   - Build 开发 (默认选中)")
    print("   - Auto 智能模式")
    print("5. 选择不同选项:")
    print("   - 选择 'Plan 分析' → 下拉框显示 'Plan 分析'")
    print("   - 选择 'Auto 智能模式' → 下拉框显示 'Auto 智能模式'")
    print("   - 选择 'Build 开发' → 下拉框显示 'Build 开发'")
    print("\n6. 打开浏览器控制台 (F12)")
    print("   应该看到日志: [UI] 模式切换到: build ( Build 开发 )")
    print("=" * 80)

    all_pass = has_select and has_default_build and has_plan_option and has_build_option and has_auto_option and not has_icons

    if all_pass:
        print("\n[SUCCESS] 所有检查通过！模式选择器已成功改为下拉菜单 ✓")
    else:
        print("\n[WARNING] 部分检查未通过")
        if not has_select:
            print("  - 下拉菜单未找到")
        if not has_default_build:
            print("  - 默认值未设置为build")
        if has_icons:
            print("  - 仍有图标残留")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    print("请确保Docker容器正在运行: docker ps")
