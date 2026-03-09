"""
Managers module for centralized management of long-running processes.

This module avoids circular imports by providing a standalone location
for manager instances that can be imported from anywhere.
"""

from app.server_manager import OpenCodeServerManager
import asyncio
import logging

logger = logging.getLogger(__name__)

# Global OpenCodeServerManager instance (lazy loaded)
_opencode_server_manager = None
_manager_lock = asyncio.Lock()


async def get_opencode_server_manager() -> OpenCodeServerManager:
    """
    Get the global OpenCodeServerManager instance (lazy loading).
    
    This function ensures that only one OpenCodeServerManager instance exists
    and provides thread-safe lazy initialization.
    
    Returns:
        OpenCodeServerManager: The global manager instance
        
    Performance characteristics:
        - First call: Starts opencode serve process (~15 seconds)
        - Subsequent calls: Returns cached instance (~2ms)
    
    Example:
        manager = await get_opencode_server_manager()
        async for chunk in manager.execute(session_id, prompt, mode):
            print(chunk)
    """
    global _opencode_server_manager
    
    if _opencode_server_manager is None:
        async with _manager_lock:
            # Double-check locking pattern
            if _opencode_server_manager is None:
                logger.info("[Managers] Initializing OpenCodeServerManager...")
                _opencode_server_manager = OpenCodeServerManager()
                logger.info("[Managers] OpenCodeServerManager initialized successfully")
    
    return _opencode_server_manager


def reset_opencode_server_manager():
    """
    Reset the global OpenCodeServerManager instance.
    
    This is primarily used for testing purposes. After calling this function,
    the next call to get_opencode_server_manager() will create a new instance.
    
    Warning: This should not be called in production code unless necessary.
    """
    global _opencode_server_manager
    _opencode_server_manager = None
    logger.warning("[Managers] OpenCodeServerManager instance reset")