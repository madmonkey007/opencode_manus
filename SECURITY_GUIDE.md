# 安全配置指南

## 🔐 重要安全说明

### 1. 环境变量配置

本项目使用环境变量来存储敏感信息。**切勿将包含真实凭证的`.env`文件提交到版本控制系统**。

### 2. 必需配置的环境变量

```bash
# OpenCode Server认证凭证（必需）
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=your_secure_password_here

# API密钥（必需）
OPENAI_API_KEY=your_api_key_here
```

### 3. 生产环境安全检查清单

- [ ] 修改默认密码`opencode-dev-2026`为强密码
- [ ] 确保`.env`文件已添加到`.gitignore`
- [ ] 验证`.env`文件未被git追踪
- [ ] 使用HTTPS（生产环境）
- [ ] 定期轮换API密钥
- [ ] 限制服务器访问权限

### 4. 安全最佳实践

#### 密码要求
- 最少12个字符
- 包含大小写字母、数字和特殊字符
- 不使用常见单词或模式

#### 示例强密码生成
```bash
# 使用openssl生成随机密码
openssl rand -base64 32

# 或使用Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. 故障排查

**认证失败错误**：
```
Authentication failed: invalid username or password
```
**解决方案**：检查`.env`文件中的凭证是否正确

**连接失败错误**：
```
Connection failed: is the server running at http://127.0.0.1:4096
```
**解决方案**：
1. 检查Docker容器是否运行：`docker ps`
2. 检查端口是否正确映射：`docker port opencode-container`

### 6. 紧急安全措施

如果凭证泄露，立即：
1. 修改所有密码和API密钥
2. 检查服务器日志是否有异常访问
3. 撤销可能泄露的API密钥

---

**注意**：`.env.example`文件包含模板配置，不包含真实凭证。复制此文件为`.env`并填入真实值。
