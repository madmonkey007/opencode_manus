import re

# 读取api.py
with open('app/api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到get_messages函数并替换
old_pattern = r'(@router\.get\("/session/{session_id}/messages"\)[^}]+raise HTTPException\(status_code=404)'

new_code = '''@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """
    获取会话的所有消息历史
    """
    # 尝试从内存/数据库获取
    messages = await session_manager.get_messages(session_id)
    
    # 如果内存中没有，尝试从磁盘恢复
    if not messages:
        import os
        session_dir = os.path.join("/app/opencode/workspace", session_id)
        
        if os.path.exists(session_dir):
            # 磁盘目录存在，自动恢复session
            logger.info(f"Auto-recovering session from disk: {session_id}")
            
            # 重新初始化session
            session = await session_manager.create_session(
                session_id=session_id,
                title=f"Recovered: {session_id}",
                version="1.0.0"
            )
            
            # 重新获取messages
            messages = await session_manager.get_messages(session_id)
    
    # 如果仍然找不到，返回404
    if not messages:
        raise HTTPException(status_code=404'''

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_code, content, count=1)
    with open('app/api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 修复成功：get_messages函数已更新")
else:
    print("⚠️ 未找到匹配的函数")
    print("尝试直接查找...")
    # 直接查找并显示
    if 'get_messages' in content:
        idx = content.find('async def get_messages')
        if idx > 0:
            snippet = content[idx:idx+500]
            print(f"找到函数，前500字符:\n{snippet}")
