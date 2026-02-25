import sys
import os

# 将项目根目录添加到 python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.prompt_enhancer import enhance_prompt


def test_enhance_prompt_creation():
    prompt = "帮我创建一个网页记录我的日常"
    enhanced = enhance_prompt(prompt)
    print(f"Original: {prompt}")
    print(f"Enhanced: {enhanced}")
    # Web 任务会有专门的 Web 规范，其中也包含了使用 Write 工具的要求
    assert "必须直接使用 Write 工具" in enhanced
    assert "必须写入单个文件（如 index.html）" in enhanced
    print("Test Creation: PASSED")


def test_enhance_prompt_edit():
    prompt = "修改 index.html 的背景色为红色"
    enhanced = enhance_prompt(prompt)
    print(f"Original: {prompt}")
    print(f"Enhanced: {enhanced}")
    assert "使用 edit 工具" in enhanced
    print("Test Edit: PASSED")


def test_enhance_prompt_generic():
    prompt = "这段代码写得怎么样？"
    enhanced = enhance_prompt(prompt)
    print(f"Original: {prompt}")
    print(f"Enhanced: {enhanced}")
    assert "使用合适的工具" in enhanced
    print("Test Generic: PASSED")


if __name__ == "__main__":
    try:
        test_enhance_prompt_creation()
        print("-" * 20)
        test_enhance_prompt_edit()
        print("-" * 20)
        test_enhance_prompt_generic()
        print("\nAll Prompts Enhanced Correctly!")
    except AssertionError as e:
        print(f"Test FAILED: {e}")
        sys.exit(1)
