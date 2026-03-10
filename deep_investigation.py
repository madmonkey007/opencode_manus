"""
深度调查opencode web的真实端口和API
"""
import subprocess
import re
import requests

print("=" * 70)
print("opencode web 深度调查")
print("=" * 70)

# 1. 获取所有监听端口
print("\n步骤1: 获取所有监听端口...")
result = subprocess.run(
    'netstat -ano | findstr "LISTENING" | findstr "127.0.0.1"',
    shell=True,
    capture_output=True,
    text=True
)

lines = result.stdout.strip().split('\n')
ports = []
for line in lines:
    if '127.0.0.1:' in line:
        match = re.search(r'127\.0\.0\.1:\s+(\d+)', line)
        if match:
            port = match.group(1)
            ports.append(port)
            print(f"  发现端口: {port}")

print(f"\n共发现 {len(ports)} 个监听端口")

# 2. 测试每个端口
print("\n步骤2: 测试每个端口是否是opencode web...")
print("-" * 70)

opencode_candidates = []

for i, port in enumerate(ports[:20], 1):  # 只测试前20个
    print(f"\n[{i}/{min(20, len(ports))}] 测试端口 {port}...", flush=True)
    
    try:
        # 测试HTTP
        response = requests.get(f"http://127.0.0.1:{port}", timeout=3)
        
        # 检查是否是opencode
        content = response.text.lower()
        
        if 'opencode' in content or ('open' in content and 'code' in content):
            print(f"  ✅ 可能是opencode web!")
            opencode_candidates.append({
                'port': port,
                'status': response.status_code,
                'content_length': len(content),
                'preview': content[:200]
            })
        elif response.status_code == 200:
            print(f"  ℹ️  HTTP 200 (但可能不是opencode)")
            if len(content) > 100:
                print(f"     预览: {content[:100]}...")
        else:
            print(f"  ⚠️  HTTP {response.status_code}")
            
    except requests.exceptions.ConnectException:
        print(f"  ❌ 连接被拒绝")
    except requests.exceptions.Timeout:
        print(f"  ⏱️  超时")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}")

# 3. 汇总
print("\n" + "=" * 70)
print("调查结果")
print("=" * 70)

if opencode_candidates:
    print(f"\n找到 {len(opencode_candidates)} 个opencode web候选:")
    for candidate in opencode_candidates:
        print(f"\n  端口: {candidate['port']}")
        print(f"  状态: {candidate['status']}")
        print(f"  内容长度: {candidate['content_length']} 字节")
        if len(candidate['preview']) > 50:
            print(f"  预览: {candidate['preview'][:200]}...")
    
    print(f"\n✅ opencode web 很可能在端口: {opencode_candidates[0]['port']}")
else:
    print("\n❌ 未找到opencode web")
    print("\n可能的原因:")
    print("  1. opencode web未启动")
    print("  2. 使用了非localhost地址（如0.0.0.0）")
    print("  3. 使用了非HTTP协议（如WebSocket）")

print("\n" + "=" * 70)
