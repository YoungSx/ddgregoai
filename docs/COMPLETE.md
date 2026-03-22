# 完成授权

## 授权页面

邮箱验证通过后，会显示授权确认页，显示：
- 登录的邮箱
- 将共享的信息（姓名、邮箱、头像）

点击"继续"按钮。

## OAuth 回调

点击"继续"后，OAuth 自动重定向到回调 URL：

```
http://localhost:1455/auth/callback?code=XXX&state=XXX&...
```

回调服务器会：
1. 接收请求
2. 提取 code 和 state
3. 显示 "Callback Received!" 页面

## 创建账号

> **警告**：**只能调用一次 create_account_from_oauth**！第一次调用后 session 即失效。

### 立即创建

收到回调后，**立即**在回调页面输入 session_id 并点击"创建账号"。

### 或用代码创建

```python
from scripts.api import Sub2APIClient
from scripts.config import load_config

config = load_config()
client = Sub2APIClient(
    config.sub2api.base_url,
    config.sub2api.admin_api_key
)

result = client.create_account_from_oauth(
    session_id="<session_id>",   # 生成OAuth时保存的
    code="<code>",               # 回调URL中的code参数
    state="<state>",             # 回调URL中的state参数
    name="User Name",
    group_ids=[1]
)

print(f"账号创建成功! ID: {result.id}")
```

### 常见错误

| 错误 | 原因 |
|------|------|
| `session not found or expired` | session 过期或已使用过 |
| `400 Bad Request` | 参数错误 |

**如果报错**：
- **不要重复调用**（会继续报错）
- 需要**重新生成 OAuth URL**，重新走整个流程

## 启动回调服务器

```bash
python scripts/callback_server.py -p 1455
```

服务器默认在后台运行。
