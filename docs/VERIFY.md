# 验证流程

## 获取验证码

当页面显示"检查您的收件箱"时，需要获取邮箱验证码。

---

## 推荐方法：使用 Klavis-strata MCP

> **这是最快、最可靠的方法**，不要用浏览器打开 Outlook 网页。

### MCP 调用

```
action: outlookMail_list_messages
server: outlook mail
category: OUTLOOK_MESSAGE
```

```python
Klavis-strata_execute_action(
    server_name="outlook mail",
    category_name="OUTLOOK_MESSAGE",
    action_name="outlookMail_list_messages",
    query_params={
        "top": "3",                                        # 获取最新3封
        "filter_query": "from/emailAddress/address contains 'openai.com'",  # 过滤OpenAI
        "orderby": "receivedDateTime desc",               # 按时间倒序
        "select": "title,receivedDateTime,bodyPreview"
    },
    include_output_fields=["title", "preview", "received"]
)
```

### 常见错误

| 你可能想用的 | 正确写法 | 说明 |
|-------------|----------|------|
| `list_emails` | `outlookMail_list_messages` | 完整action名称 |
| `search_emails` | `outlookMail_list_messages` + filter | 使用filter参数 |
| `maxResults` | `top` | 参数名是`top`不是`maxResults` |

---

## 输入验证码

1. 从 MCP 返回中提取验证码（第一封邮件的标题或 preview）
2. 在页面输入验证码
3. 点击"继续"

---

## 验证码错误处理

> **关键**：验证码错误后，**不要刷新页面**，立即执行以下步骤：

1. **点击"重新发送电子邮件"** 按钮
2. **等待 5-10 秒** 让邮件到达
3. **用 MCP 重新获取** 最新邮件
4. **取最新那封的验证码**（不是之前那封）
5. 输入新验证码

### 错误做法 ❌

```
验证码错误 → 刷新页面 → 去Outlook网页查看 → 白等 → 用旧验证码 → 再次错误
```

### 正确做法 ✅

```
验证码错误 → 点击重新发送 → MCP获取新邮件 → 输入新验证码 → 成功
```

---

## 验证超时

如果页面过期，需要重新开始整个 OAuth 流程（生成新 URL）。

---

## 邮件过滤建议

- 验证码邮件来自 `otp@tm1.openai.com` 或 `noreply@tm.openai.com`
- 邮件标题格式：`Your ChatGPT code is XXXXXX` 或 `你的 ChatGPT 代码为 XXXXXX`
- `bodyPreview` 中也包含验证码
