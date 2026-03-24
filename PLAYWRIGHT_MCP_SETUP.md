# 浏览器自动化工具配置指南

## 问题说明

您提到安装过Chrome DevTools，但我在当前环境中无法使用。经过检查发现：

### 问题根源
1. ✅ `permissions.allow`中**已列出**浏览器工具：
   - `mcp__chrome-devtools`
   - `mcp__Playwright`
   - `mcp__playwright`

2. ❌ 但**缺少MCP服务器配置**，导致工具无法使用

### 解决方案

已在项目中创建`.mcp.json`配置文件（Commit `d9f4d9d`），配置内容：

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"],
      "env": {
        "HEADLESS": "true"
      }
    }
  }
}
```

## 📋 启用步骤

### 步骤1：重启Claude Code

**重要**：必须重启Claude Code才能加载新的MCP服务器配置

1. 完全退出Claude Code
2. 重新打开Claude Code
3. 打开opencode项目

### 步骤2：批准MCP服务器

重启后，Claude Code会提示：
```
发现项目配置的MCP服务器：playwright
是否启用？
```

**点击"启用"**

### 步骤3：验证安装

首次使用时，npx会自动安装playwright-mcp-server：
```bash
npx -y @executeautomation/playwright-mcp-server
```

可能需要几分钟下载依赖。

### 步骤4：验证可用性

重启后，我可以使用浏览器自动化工具：
- 打开浏览器
- 访问页面
- 执行JavaScript
- 截图
- 等待页面加载

## 🧪 测试Preview事件修复

启用Playwright后，我可以：

### 自动化测试1：访问页面并检查元素

```javascript
// 访问本地服务
await page.goto('http://localhost:8089')

// 检查页面标题
const title = await page.title()
console.log('页面标题:', title)

// 检查是否有错误
const errors = await page.evaluate(() => {
    return window.errors || []
})
```

### 自动化测试2：运行任务并验证

```javascript
// 1. 访问页面
await page.goto('http://localhost:8089')

// 2. 输入任务
await page.fill('textarea[name="prompt"]', '帮我写一个简单的HTML页面')

// 3. 点击提交
await page.click('button[type="submit"]')

// 4. 等待完成
await page.waitForSelector('.task-complete', { timeout: 30000 })

// 5. 检查preview面板
const previewVisible = await page.isVisible('.file-preview')
console.log('Preview面板可见:', previewVisible)

// 6. 截图保存
await page.screenshot({ path: 'preview-test.png' })
```

### 自动化测试3：监控控制台日志

```javascript
// 监听控制台事件
page.on('console', msg => {
    if (msg.text().includes('preview')) {
        console.log('📨 Preview事件:', msg.text())
    }
})

// 运行任务...
// 检查是否有preview事件
```

## 🎯 现在可以做什么

启用Playwright后，我可以帮您：

1. **自动化测试**
   - 自动打开浏览器
   - 运行测试任务
   - 验证preview事件
   - 截图保存证据

2. **调试前端问题**
   - 检查DOM元素
   - 执行JavaScript代码
   - 监控网络请求
   - 分析控制台日志

3. **验证修复效果**
   - 测试文件预览功能
   - 验证打字机效果
   - 检查交付面板

## ⚠️ 注意事项

### 首次使用
- npx会下载playwright-mcp-server（可能需要几分钟）
- 需要Node.js环境
- 首次启动浏览器可能需要下载Chromium

### 性能
- 无头模式（HEADLESS=true）不显示浏览器窗口
- 如需看到浏览器，设置`HEADLESS=false`
- 浏览器自动化比手动测试慢

### 兼容性
- Playwright支持Chrome、Firefox、Safari
- 默认使用Chromium
- 可以配置使用系统浏览器

## 🔧 故障排查

### 问题1：MCP服务器无法启动

**症状**：重启Claude Code后没有提示启用playwright

**解决**：
1. 检查.mcp.json是否在项目根目录
2. 确认JSON格式正确
3. 查看Claude Code日志

### 问题2：npx命令失败

**症状**：提示"npx不是内部或外部命令"

**解决**：
1. 安装Node.js：https://nodejs.org/
2. 验证安装：`npx --version`

### 问题3：浏览器无法启动

**症状**：超时或连接失败

**解决**：
1. 检查防火墙设置
2. 尝试设置`HEADLESS=false`
3. 查看Playwright日志

## 📚 相关资源

- **Playwright MCP Server**: https://github.com/executeautomation/playwright-mcp-server
- **Playwright文档**: https://playwright.dev/
- **Claude Code MCP文档**: https://github.com/anthropics/claude-code/tree/main/docs/mcp.md

## 🚀 下一步

1. **重启Claude Code**（最重要！）
2. 启用playwright MCP服务器
3. 告诉我进行测试
4. 我会自动化测试preview事件修复

---

**配置文件**: `.mcp.json`
**Commit**: `d9f4d9d`
**状态**: ✅ 已配置，等待重启Claude Code
