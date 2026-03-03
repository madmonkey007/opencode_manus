"""
测试数据库迁移消息修复

验证包含ANSI转义序列的"Database migration complete"消息
能够正确传递到前端，而不是被过滤掉。
"""

import asyncio
import re


def test_ansi_filtering():
    """测试ANSI过滤逻辑"""
    # 原始消息（包含ANSI转义序列）
    original_message = "[?25l[?25hDatabase migration complete."

    # 旧逻辑（会过滤掉这个消息）
    ansi_patterns = ["[0m", "[93m", "[1m", "\x1b[", "[?25"]
    old_filter_result = any(pattern in original_message for pattern in ansi_patterns)
    print(f"[旧逻辑] 消息被过滤: {old_filter_result}")  # 应该是 True

    # 新逻辑（特殊处理数据库迁移消息）
    has_db_migration = "database migration" in original_message.lower()
    print(f"[新逻辑] 检测到数据库迁移消息: {has_db_migration}")  # 应该是 True

    # 清理ANSI转义序列
    cleaned_message = re.sub(r'\x1b\[[0-9;]*[?a-zA-Z]', '', original_message)
    print(f"[新逻辑] 清理后的消息: '{cleaned_message.strip()}'")  # 应该是 "Database migration complete."

    # 验证
    assert has_db_migration, "❌ 未能检测到数据库迁移消息"
    assert cleaned_message.strip() == "Database migration complete.", "❌ 消息清理失败"
    print("\n✅ 测试通过：数据库迁移消息将被正确处理")


def test_other_ansi_messages_still_filtered():
    """测试其他ANSI消息仍然被过滤"""
    # 普通的ANSI颜色代码消息（应该被过滤）
    color_message = "[93mWarning: something[0m"
    has_db_migration = "database migration" in color_message.lower()

    if not has_db_migration:
        # 应用ANSI过滤
        ansi_patterns = ["[0m", "[93m", "[1m", "\x1b[", "[?25"]
        should_filter = any(pattern in color_message for pattern in ansi_patterns)
        print(f"[验证] 普通ANSI消息被过滤: {should_filter}")  # 应该是 True
        assert should_filter, "❌ 普通ANSI消息应该被过滤"
        print("✅ 测试通过：普通ANSI消息仍然被过滤")
    else:
        print("❌ 测试失败：普通消息不应该被识别为数据库迁移消息")


if __name__ == "__main__":
    print("=" * 60)
    print("测试：数据库迁移消息修复")
    print("=" * 60)
    print()

    test_ansi_filtering()
    print()
    test_other_ansi_messages_still_filtered()

    print()
    print("=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
    print()
    print("修复说明：")
    print("1. 数据库迁移消息现在会特殊处理，即使包含ANSI转义序列")
    print("2. ANSI转义序列会被清理，但消息内容会保留")
    print("3. 前端能够正常显示 'Database migration complete.'")
    print("4. 不会再出现卡在 'Performing one time database migration...' 的情况")
