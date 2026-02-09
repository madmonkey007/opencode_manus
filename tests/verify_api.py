"""Simple API verification"""
import sys
sys.path.insert(0, 'app')

try:
    print("Importing api module...")
    from api import router, session_manager
    print("SUCCESS: api module imported")
    print(f"SessionManager: {session_manager}")
    print(f"Router: {router}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\nTesting SessionManager...")
    import asyncio

    async def test():
        session = await session_manager.create_session("Test Session")
        print(f"SUCCESS: Created session {session.id}")

        retrieved = await session_manager.get_session(session.id)
        print(f"SUCCESS: Retrieved session {retrieved.id}")

        return session

    result = asyncio.run(test())
    print(f"Final session ID: {result.id}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nAll basic tests passed!")
