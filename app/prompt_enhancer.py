import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("opencode.enhancer")


def enhance_prompt(user_prompt: str, mode: str = "auto") -> str:
    """
    智能增强用户提示词，添加必要的技术指导

    目的：将用户的自然语言需求转换为 Agent 可以明确执行的指令
    原则：
    1. 保持用户的原始意图
    2. 识别任务类型并补充技术细节
    3. 不改变用户想要实现的目标
    """

    prompt_lower = user_prompt.lower()

    # 如果是 plan 或 build 模式，放松对子智能体和任务工具的限制
    # 官方的 plan 和 build 智能体内部依赖这些功能
    is_agent_mode = mode in ["plan", "build"]

    # 检测任务类型
    task_indicators = {
        "code_creation": [
            "创建",
            "生成",
            "写",
            "设计",
            "开发",
            "实现",
            "build",
            "create",
            "make",
            "generate",
            "design",
            "implement",
            "write",
        ],
        "file_operation": [
            "文件",
            "保存",
            "存储",
            "本地",
            "file",
            "save",
            "store",
            "local",
        ],
        "web_development": [
            "网页",
            "网站",
            "前端",
            "html",
            "css",
            "javascript",
            "web",
            "website",
            "frontend",
            "page",
            "界面",
            "ui",
        ],
        "code_edit": [
            "修改",
            "编辑",
            "改变",
            "更新",
            "修复",
            "edit",
            "modify",
            "change",
            "update",
            "fix",
            "refactor",
        ],
    }

    # 统计匹配的任务类型
    detected_tasks = []
    for task_type, keywords in task_indicators.items():
        if any(keyword in prompt_lower for keyword in keywords):
            detected_tasks.append(task_type)

    # 根据检测到的任务类型添加增强指令
    enhancements = []

    # 代码创建任务的增强
    if "code_creation" in detected_tasks or "web_development" in detected_tasks:
        if (
            "file_operation" in detected_tasks
            or "本地" in user_prompt
            or "存储" in user_prompt
        ):
            # 明确要求使用正确的工具写入完整代码
            enhancements.append(
                """
【重要技术要求】
1. 必须使用 file_editor 或 write 工具创建文件
2. 写入完整的、可直接运行的代码内容
3. 不要只创建空文件或使用 touch 命令
4. 确保每个文件都包含完整的实现代码
"""
            )

    # Web 开发任务的额外指导
    if "web_development" in detected_tasks:
        if is_agent_mode:
            # Agent 模式下允许任务拆分
            enhancements.append(
                """
【Web 开发规范】
- HTML: 包含完整的文档结构和语义化标签
- CSS: 包含响应式设计、配色方案和布局
- JavaScript: 包含完整的交互逻辑和功能实现
"""
            )
        else:
            # 非 Agent 模式（auto）维持严格限制以保证单轮成功率
            enhancements.append(
                """
【Web 开发规范】
- HTML: 包含完整的文档结构和语义化标签
- CSS: 包含响应式设计、配色方案和布局
- JavaScript: 包含完整的交互逻辑和功能实现

【关键限制】
1. 必须直接使用 Write 工具创建完整的 HTML 文件
2. 禁止使用 task 工具或其他代理工具
3. 所有代码必须写入单个文件（如 index.html）
4. 不要创建子会话或后台任务
"""
            )


    # 代码编辑任务的增强
    if "code_edit" in detected_tasks:
        enhancements.append(
            """
【代码编辑要求】
1. 使用 edit 工具精确修改代码
2. 保持代码风格一致
3. 确保修改后的代码可以正常运行
"""
        )

    # 如果没有检测到特定任务，添加通用指导
    if not enhancements:
        # 检测是否涉及任何编程任务
        programming_keywords = ["代码", "程序", "功能", "feature", "function", "code"]
        if any(keyword in prompt_lower for keyword in programming_keywords):
            enhancements.append(
                """
【执行要求】
- 使用合适的工具完成任务
- 确保输出完整、可运行的代码或配置
- 验证实现的正确性
"""
            )

    # 组合最终提示词
    if enhancements:
        enhanced_prompt = f"{user_prompt}\n\n{''.join(enhancements)}"
        logger.info(f"Prompt enhanced: detected tasks={detected_tasks}")
        return enhanced_prompt

    return user_prompt
