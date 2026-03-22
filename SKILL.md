---
name: openai-ddg-account-registration
description: "OpenAI + DuckDuckGo 账号注册。使用浏览器操作 + Klavis-strata MCP 读取验证码 + Sub2API 创建账号。"
---

# OpenAI + DuckDuckGo 账号注册

## 流程

```
启动服务器 → 生成 OAuth URL → 浏览器注册 → 自动创建账号
```

## 步骤

### 1. 启动回调服务器

```bash
python scripts/callback_server.py -p 1455
```

### 2. 生成 OAuth URL

```python
from scripts.api import *
client = Sub2APIClient(*load_config().sub2api)
result = client.generate_auth_url()
print(f"Auth URL: {result.auth_url}")
```

### 3. 浏览器注册

OAuth URL → 点击注册 → 邮箱/密码 → 个人信息 → 邮箱验证 → 授权

### 4. 获取结果

回调服务器会自动创建账号。通过轮询状态文件获取结果：

```python
from scripts.state import get_state_manager
state_manager = get_state_manager()
notification = state_manager.get_agent_notification()
print(f"Status: {notification['status']}")
print(f"Account ID: {notification['account_id']}")
```

---

## 异常处理

| 情况 | 处理 |
|------|------|
| 邮箱验证 | [docs/VERIFY.md](docs/VERIFY.md) |
| 电话验证 | [docs/LOGIN.md](docs/LOGIN.md) |
| 创建失败 | 重试一次，失败后通过状态文件通知 |

---

## ⚠️ 关键警告

1. **不要重复调用 create_account_from_oauth** - session 只能使用一次
2. **每次都要重新生成 OAuth URL** - 不能复用旧的 session
3. **验证码必须用 MCP 获取** - 不要用浏览器Outlook

---

## 详细文档

- [注册流程](docs/REGISTER.md)
- [验证码获取](docs/VERIFY.md) ← **必读**
- [登录流程](docs/LOGIN.md)
- [完成授权](docs/COMPLETE.md)
