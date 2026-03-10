import requests
import subprocess
import re

print("opencode web 深度调查")
print("=" * 70)

# 1. 获取所有监听端口
print("\n步骤1: 获取所有监听端口...")
result = subprocess.run(
    'netstat -ano | findstr "LISTENING" | findstr "127.0.0.1"',
    shell=True, capture_output=True, text=True
)

ports = []
for line in result.stdout.strip().split('\n'):
    if '127.0.0.1:' in line:
        match = re.search(r'127\.0\.0\.1:\s+(\d+)', line)
        if match:
            ports.append(match.group(1))

print(f"发现 {len(ports)} 个监听端口")

# 2. 测试每个端口
print("\n步骤2: 测试每个端口...")
print("-" * 70)

opencode_candidates = []

for i, port in enumerate(ports[:15], 1):
    print(f"[{i}/{min(15, len(ports))}] 测试端口 {port}...", flush=True)
    
    try:
        response = requests.get(f"http://127.0.0.1:{port}", timeout=3)
        content = response.text.lower()
        
        if 'opencode' in content or ('open' in content and 'code' in content):
            print(f"  ✅ 可能是opencode web!")
            opencode_candidates.append({
                'port': port,
                'status': response.status_code,
                'preview': content[:300]
            })
        elif response.status_code == 200:
            print(f"  ℹ️  HTTP 200")
            if len(content) > 50:
                print(f"     预览: {content[:100]}...")
        else:
            print(f"  ⚠️  HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 连接被拒绝")
    except requests.exceptions.Timeout:
        print(f"  ⏱️ 超时")

# 3. 汇总
print("\n" + "=" * 70)
print("调查结果")
print("=" * 70)

if opencode_candidates:
    print(f"\n找到 {len(opencode_candidates)} 个opencode候选:")
    for c in opencode_candidates:
        print(f"\n端口: {c['port']}")
        print(f"状态: {c['status']}")
        if c['preview'] and len(c['preview']) > 20:
            print(f"内容预览: {c['preview'][:200]}...")
    
    print(f"\n✅ opencode web 很可能在: {opencode_candidates[0]['port']}")
    print(f"\n下一步: 在浏览器中访问 http://127.0.0.1:{opencode_candidates[0]['port']}")
else:
    print("\n未找到opencode web")
    print("\n可能原因:")
    print("  1. opencode web未启动")
    print("  2. 使用了0.0.0.0而不是127.0.0.1")
    print("  3. 使用了非HTTP协议")

# 4. 测试找到的端口
if opencode_candidates:
    target_port = opencode_candidates[0]['port']
    print(f"\n步骤3: 深度测试端口 {target_port}...")
    
    try:
        # 测试根路径
        resp = requests.get(f"http://127.0.0.1:{target_port}/", timeout=5)
        print(f"根路径: HTTP {resp.status}")
        
        # 测试可能的API端点
        endpoints = [
            "/session",
            "/api/session",
            "/sessions",
            "/api/sessions",
            "/openapi.json",
            "/docs"
        ]
        
        for endpoint in endpoints:
            try:
                resp = requests.get(f"http://127.0.0.1:{target_port}{endpoint}", timeout=3)
                if resp.status == 200:
                    print(f"  ✅ GET {endpoint}: HTTP 200")
                else:
                    print(f"  ⚠️  GET {endpoint}: HTTP {resp.status}")
            except:
                print(f"  ❌ GET {endpoint}: 失败")
    except Exception as e:
        print(f"❌ 错误: {e}")

print("\n" + "=" * 70)
