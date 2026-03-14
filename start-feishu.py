#!/usr/bin/env python3
"""
OpenCode IM Bridge Server Launcher - Feishu Edition
Loads Feishu configuration from .env.feishu and starts the server
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
    print("OpenCode IM Bridge Server - Feishu Edition")
    print("=" * 60)
    print()

    # Load .env.feishu if exists
    env_file = Path('.env.feishu')
    if env_file.exists():
        print(f"[INFO] Loading configuration from {env_file}")
        feishu_config = load_env_file(env_file)

        # Set environment variables
        for key, value in feishu_config.items():
            os.environ[key] = value
            # Mask sensitive values
            if 'TOKEN' in key or 'SECRET' in key or 'KEY' in key:
                display_value = '***configured***' if value else '(not set)'
            elif 'WEBHOOK' in key and value:
                # Show first 50 chars of webhook URL
                display_value = f'{value[:50]}...' if len(value) > 50 else value
            else:
                display_value = value if value else '(not set)'

            print(f"  {key}: {display_value}")

        print()
        print("[OK] Configuration loaded")
    else:
        print("[WARN] .env.feishu file not found")
        print()
        print("Please create .env.feishu with your Feishu webhook:")
        print("  FEISHU_ENABLE=true")
        print("  IM_PLATFORM=feishu")
        print("  FEISHU_WEBHOOK_URL=your_webhook_url")
        print()
        print("Or run: start-feishu.bat (Windows)")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

    # Check if Feishu is enabled
    if os.getenv('FEISHU_ENABLE') == 'true':
        print()
        print("[Feishu Bot] Configuration:")
        print(f"  Platform: {os.getenv('IM_PLATFORM', 'feishu')}")
        webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '')
        if webhook_url:
            print(f"  Webhook: {webhook_url[:50]}...")
        else:
            print(f"  Webhook: (not set)")
        print()
    else:
        print("[WARN] Feishu Bot is not enabled")
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
