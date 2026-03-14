# OpenCode飞书交互机器人 - 快速开始

## 🎯 功能说明

在飞书群里@机器人提交OpenCode任务，完成后自动接收结果通知。

**使用示例**：
```
你在群里发送：@opencode 创建一个Python脚本，计算斐波那契数列前10项

机器人：
1. 接收消息
2. 提交任务到OpenCode
3. OpenCode执行任务
4. 完成后自动在群里发送结果
```

---

## 🚀 快速开始

### 第1步：创建飞书应用

1. **登录飞书开放平台**
   - 访问：https://open.feishu.cn/
   - 使用飞书账号登录

2. **创建企业应用**
   - 点击"创建企业自建应用"
   - 应用名称：`OpenCode Bot`
   - 应用描述：`OpenCode任务执行助手`

3. **获取凭证**
   - AppID：自动生成（复制保存）
   - AppSecret：点击"查看"生成（复制保存）

4. **配置权限**
   - 开通权限：机器人、获取群组信息、发送消息
   - 这些都是基础权限，很容易申请

5. **配置事件订阅**
   - 订阅事件：`im.message.receive_v1`
   - 请求方式：HTTP
   - 回调URL：需要公网IP（见下方说明）
   - 加密方式：不启用（本地开发）

6. **添加机器人到群**
   - 在应用管理中找到机器人
   - 点击"添加到群"
   - 选择你的开发群

---

### 第2步：配置本地服务器

1. **编辑配置文件**
   - 文件：`configs/feishu-config.json`
   - 填入你的AppID和AppSecret

```json
{
  "app_id": "cli_your_actual_app_id",
  "app_secret": "your_actual_app_secret",
  "encrypt_key": "",
  "verification_token": "",
  "event_port": 3000,
  "opencode_api": "http://localhost:8080",
  "bot_name": "@opencode"
}
```

2. **启动服务**
   ```bash
   # 方式1：使用启动脚本
   start-feishu-bot.bat

   # 方式2：手动启动
   node feishu-event-listener.js
   ```

---

### 第3步：配置公网回调（重要！）

飞书需要公网IP才能推送事件到你的本地服务器。

**方案1：使用ngrok（推荐，测试用）**

```bash
# 1. 下载ngrok：https://ngrok.com/download
# 2. 解压并运行
ngrok http 3000

# 3. 复制公网URL（如 https://abc123.ngrok.io）
# 4. 在飞书开放平台设置回调URL为：
#    https://abc123.ngrok.io/feishu/events
```

**方案2：内网穿透（长期使用）**
- 使用frp、花生壳等工具
- 需要有公网服务器

**方案3：云服务器**
- 部署到阿里云、腾讯云等
- 获得固定公网IP

---

### 第4步：测试

1. **确保服务运行**
   - Feishu Event Listener (port 3000)
   - IM Bridge (port 18080)
   - OpenCode服务器 (port 8080)

2. **在飞书群测试**
   ```
   @opencode 创建一个Python脚本，输出Hello World
   ```

3. **预期结果**
   - 服务器控制台显示接收到事件
   - OpenCode开始执行任务
   - 完成后飞书群收到结果消息

---

## 🔧 配置说明

### 飞书事件订阅

**事件类型**：`im.message.receive_v1`

**订阅方式**：HTTP

**回调URL**：你的公网地址 + `/feishu/events`
- ngrok测试：`https://xxx.ngrok.io/feishu/events`
- 云服务器：`http://your-server-ip:3000/feishu/events`

**加密**：不启用（开发阶段）

**验证Token**：随意填写（开发阶段）

---

## 📝 命令格式

### 基本格式

```
@opencode <任务描述>
```

### 示例

```
@opencode 创建一个Python脚本，实现快速排序
@opencode 用JavaScript写一个函数，反转字符串
@opencode 帮我写一个贪吃蛇游戏
```

### 注意事项

1. **必须@opencode**：否则机器人不会响应
2. **任务描述清晰**：描述越详细，结果越好
3. **等待完成**：任务完成后会自动通知，无需催促
4. **只能群聊**：暂不支持私聊（可以后续添加）

---

## 🛠️ 故障排查

### 问题1：机器人没有响应

**可能原因**：
- 事件订阅未配置
- 回调URL不可访问
- AppID/AppSecret配置错误

**解决方案**：
1. 检查飞书开放平台的事件订阅状态
2. 使用ngrok获取公网URL
3. 验证配置文件中的凭证

### 问题2：接收到事件但没有提交任务

**可能原因**：
- OpenCode API未运行
- 端口或URL配置错误

**解决方案**：
1. 确认OpenCode服务器运行中
2. 检查opencode_api配置
3. 查看服务器控制台日志

### 问题3：任务提交但没有收到结果

**可能原因**：
- IM Bridge未运行
- 飞书webhook配置错误

**解决方案**：
1. 确保IM Bridge运行在18080端口
2. 检查.env.feishu中的webhook URL
3. 查看IM Bridge日志

---

## 🎯 后续扩展

当前版本支持基本功能，可以扩展：

1. **支持更多命令**
   ```
   @opencode status  # 查询任务状态
   @opencode cancel   # 取消当前任务
   ```

2. **支持私聊**
   - 允许私聊机器人提交任务
   - 结果私聊返回

3. **任务队列**
   - 支持多个任务排队
   - 查询队列状态

---

## 📚 参考文档

- **飞书开放平台**：https://open.feishu.cn/
- **事件订阅文档**：https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjYxUjY
- **机器人开发指南**：https://open.feishu.cn/document/ukTMukTMukTM/ukTNwUjYxUjY

---

## ✅ 验收清单

- [ ] 飞书应用创建完成
- [ ] AppID和AppSecret已配置
- [ ] 事件订阅已设置
- [ ] 机器人已添加到群
- [ ] 本地服务器启动成功
- [ ] ngrok（或其他工具）运行正常
- [ ] 测试@消息成功
- [ ] OpenCode任务执行成功
- [ ] 结果通知发送到飞书群

---

**开始配置吧！** 🚀
