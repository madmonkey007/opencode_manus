#!/usr/bin/env python3
"""
OpenCode IM Bridge Server Launcher
Loads QQ configuration from .env.qq and starts the server
"""
import os
import sys
import subprocess
from pathlib import Path

def load_env_file(env_file):
    """Load environment variables from .env file"""
    if not env_file.exists():
        return {}

    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars

def main():
    print("=" * 60)
    print("OpenCode IM Bridge Server Launcher")
    print("=" * 60)
    print()

    # Load .env.qq if exists
    env_file = Path('.env.qq')
    if env_file.exists():
        print(f"[INFO] Loading configuration from {env_file}")
        qq_config = load_env_file(env_file)

        # Set environment variables
        for key, value in qq_config.items():
            os.environ[key] = value
            # Mask sensitive values
            if 'TOKEN' in key or 'KEY' in key:
                display_value = '***configured***' if value else '(not set)'
            else:
                display_value = value if value else '(not set)'

            print(f"  {key}: {display_value}")

        print()
        print("[OK] Configuration loaded")
    else:
        print("[WARN] .env.qq file not found")
        print()
        print("Please create .env.qq with your QQ Bot configuration:")
        print("  QQ_ENABLE=true")
        print("  QQ_BOT_TYPE=official")
        print("  QQ_APP_ID=your_app_id")
        print("  QQ_TOKEN=your_token")
        print("  QQ_TARGETS=user:your_openid")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

    # Check if QQ is enabled
    if os.getenv('QQ_ENABLE') == 'true':
        print()
        print("[QQ Bot] Configuration:")
        print(f"  Type: {os.getenv('QQ_BOT_TYPE', 'official')}")
        print(f"  AppID: {os.getenv('QQ_APP_ID', '(not set)')}")
        print(f"  Target: {os.getenv('QQ_TARGETS', '(not set)')}")
        print()
    else:
        print("[WARN] QQ Bot is not enabled")
        print()

    # Start IM Bridge server
    print("[START] IM Bridge Server (port 18080)...")
    print()

    try:
        # Start the server
        process = subprocess.Popen(
            ['node', 'im-bridge-server.js'],
            env=os.environ,
            cwd=Path.cwd()
        )

        print("[OK] IM Bridge server started")
        print()
        print("Test: curl -X POST http://localhost:18080/test/event \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"event_type\":\"complete\",\"data\":{\"result\":\"success\"}}'")
        print()
        print("Press Ctrl+C to stop the server")
        print()

        # Wait for process
        process.wait()

    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
