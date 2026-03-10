"""
深度调查opencode web的端口和API
"""
import subprocess
import re

# 1. 查找opencode进程实际监听的端口
print("=" * 70)
print("调查1: 查找opencode进程实际监听的端口")
print("=" * 70)

# 获取opencode进程的PID
try:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq opencode.exe"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print("opencode进程:")
    for line in result.stdout.split('\n'):
        if 'opencode.exe' in line:
            print(f"  {line}")
            
except Exception as e:
    print(f"Error: {e}")

# 2. 查找所有监听端口
print("\n" + "=" * 70)
print("调查2: 查找localhost上所有监听端口")
print("=" * 70)

try:
    result = subprocess.run(
        'netstat -ano | findstr "LISTENING" | findstr "127.0.0.1"',
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    ports = []
    for line in result.stdout.split('\n'):
        if '127.0.0.1:' in line and 'LISTENING' in line:
            # 提取端口号
            match = re.search(r'127\.0\.0\.1:(\d+)', line)
            if match:
                port = match.group(1)
                ports.append(port)
                print(f"发现端口: {port}")
    
    print(f"\n共发现 {len(ports)}个监听端口")
    
    # 3. 测试每个端口
    print("\n" + "=" * 70)
    print("调查3: 测试每个端口是否是opencode web")
    print("=" * 70)
    
    import time
    
    for port in ports[:10]:  # 只测试前10个
        print(f"\n测试端口 {port}...", flush=True)
        try:
            result = subprocess.run(
                f'curl -m 3 http://127.0.0.1:{port}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                # 查找opencode相关的关键词
                if 'opencode' in result.stdout.lower() or 'title' in result.stdout.lower():
                    print(f"  ✅ 可能是opencode web!")
                    print(f"  预览: {result.stdout[:200]}...")
                else:
                    print(f"  ❌ 不是opencode (响应: {result.stdout[:100]}...")
            else:
                print(f"  ⚠️ 无响应")
                
        except Exception as e:
            print(f"  ❌ 错误: {str(e)[:50]}")
        
        time.sleep(0.5)

except Exception as e:
    print(f"\n错误: {e}")

print("\n" + "=" * 70)
print("调查完成")
print("=" * 70)
