# 登录流程（电话验证分支）

## 何时使用

**当注册流程中遇到电话验证页面时**，跳过电话验证，改用登录流程。

> **注意**：电话验证页面出现 ≠ 注册失败，而是 OpenAI 的风控措施。

---

## 流程

```
注册遇到电话验证 → 生成新 OAuth URL → 登录邮箱 → 邮箱验证 → 授权 → 完成
```

---

## 详细步骤

### 1. 生成新 OAuth URL

使用 Sub2API 生成新的授权链接。

> **重要**：**这是新的 session**，旧的 session 不能复用。

```python
result = client.generate_auth_url()
print(f"Session ID: {result.session_id}")  # 保存！
```

### 2. 登录

在 OAuth 页面：
1. 输入之前使用的邮箱（格式：`word-word-word@duck.com`）
2. 输入密码
3. 点击继续

### 3. 邮箱验证

**必须用 Klavis-strata MCP** 获取验证码（见 [docs/VERIFY.md](VERIFY.md)）。

> **常见错误**：不要用之前注册时的验证码，每次登录的验证码都是新的。

### 4. 完成授权

验证通过后，出现授权确认页。点击"继续"。

### 5. OAuth 回调

OAuth 自动重定向到回调服务器。

### 6. 创建账号

**立即调用 API 创建账号**（不要重复调用）。

```python
result = client.create_account_from_oauth(
    session_id="<新session_id>",
    code="<回调code>",
    state="<回调state>",
    name="User Name",
    group_ids=[1]
)
```

---

## 注意事项

- 使用与注册**相同的邮箱和密码**
- **每次都需要生成新的 OAuth URL**，旧 session 不能复用
