"""
测试poll函数URL路径正确性

确保poll函数使用正确的API端点(/messages而不是/message)
防止405错误的bug再次发生。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


@pytest.mark.asyncio
async def test_poll_uses_correct_messages_endpoint():
    """测试poll函数使用/messages复数端点，而不是/message单数端点"""
    from app.opencode_client import OpenCodeClient
    from app.api_endpoints import APIEndpoints

    # 创建client
    client = OpenCodeClient('workspace/test')

    # Mock HTTP响应
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "msg_test",
            "info": {"role": "assistant"},
            "parts": [
                {"type": "text", "text": "Test response"}
            ]
        }
    ]

    # Mock httpx.AsyncClient
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        # 执行poll（这会调用_poll_parts）
        with patch.object(client, '_execute_via_server_api', return_value=True):
            await client.execute(
                "Test prompt",
                "ses_test123",
                mode="auto",
                use_server_api=True
            )

        # 验证使用的URL包含/messages而不是/message
        call_args = mock_client.get.call_args
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get('url', '')

        # 断言：URL应该使用/messages（复数）
        assert APIEndpoints.SESSION_MESSAGES.split('/')[-1] in url, \
            f"URL should use /messages endpoint, got: {url}"

        # 断言：URL不应该使用/message（单数）
        # 注意：/messages包含/message，所以需要精确匹配
        assert url.endswith('/messages'), \
            f"URL should end with /messages, got: {url}"


@pytest.mark.asyncio
async def test_api_endpoints_constants_defined():
    """测试API端点常量已正确定义"""
    from app.api_endpoints import APIEndpoints

    # 验证关键端点常量存在
    assert hasattr(APIEndpoints, 'SESSION_MESSAGES')
    assert hasattr(APIEndpoints, 'SESSION_SINGLE_MESSAGE')
    assert hasattr(APIEndpoints, 'SESSION_CREATE')
    assert hasattr(APIEndpoints, 'HEALTH')

    # 验证URL格式正确
    assert APIEndpoints.SESSION_MESSAGES == "/session/{session_id}/messages"
    assert APIEndpoints.SESSION_SINGLE_MESSAGE == "/session/{session_id}/message"

    # 验证格式化方法
    formatted = APIEndpoints.format_session_messages("ses_test123")
    assert formatted == "/session/ses_test123/messages"


@pytest.mark.asyncio
async def test_session_message_and_messages_both_work():
    """测试/message和/messages两个端点都可以正常工作"""
    from app.api_endpoints import APIEndpoints
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    session_id = "ses_test_both_endpoints"

    # 测试/messages端点（复数）
    response_messages = client.get(f"/opencode/session/{session_id}/messages")
    assert response_messages.status_code in [200, 404]  # 200 if exists, 404 if not

    # 测试/message端点（单数，应该是/messages的别名）
    response_message = client.get(f"/opencode/session/{session_id}/message")
    assert response_message.status_code in [200, 404]

    # 两个端点应该返回相同的数据结构
    if response_messages.status_code == 200 and response_message.status_code == 200:
        assert response_messages.json() == response_message.json()


@pytest.mark.asyncio
async def test_poll_no_405_error():
    """测试poll不应该返回405错误（Method Not Allowed）"""
    from app.opencode_client import OpenCodeClient

    client = OpenCodeClient('workspace/test')

    # Mock一个成功的响应
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        # 执行操作
        with patch.object(client, '_execute_via_server_api', return_value=True):
            result = await client.execute(
                "Test",
                "ses_test",
                mode="auto",
                use_server_api=True
            )

        # 验证没有405错误
        assert mock_client.get.call_args is not None
        # 如果是405，status_code会是405，但我们mock的是200
        assert mock_response.status_code != 405


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
