"""Quick test for managers"""
import sys
sys.path.insert(0, 'app')

from managers import SessionManager
from models import MessageRole, generate_message_id
import asyncio

async def test():
    sm = SessionManager()
    session = await sm.create_session('Test Session')
    print(f'Session created: {session.id}')

    message = Message(
        id=generate_message_id(),
        session_id=session.id,
        role=MessageRole.USER
    )
    await sm.add_message(message)
    print(f'Message added: {message.id}')

    count = await sm.get_message_count(session.id)
    print(f'Message count: {count}')

    print('✅ All tests passed!')

if __name__ == '__main__':
    asyncio.run(test())
