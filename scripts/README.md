# ChatGPT 账号管理脚本 v7.0

## 📁 Python脚本列表

| 脚本 | 用途 |
|------|------|
| `playwright_register.py` | 全自动注册（Playwright自动化） |
| `callback_server.py` | OAuth 回调服务器 |
| `verify_accounts.py` | 验证账号状态 |
| `cleanup_accounts.py` | 清理无效账号 |
| `setup.py` | 配置向导 |

## 🚀 快速开始

### 1. 初始化配置

```bash
python -m scripts.setup
```

### 2. 启动回调服务器

```bash
python -m scripts.callback_server -p 1455
```

### 3. 全自动注册

```bash
python -m scripts.playwright_register -e "a@duck.com,b@duck.com" -p "Pass1,Pass2" -c 2
```

### 4. 验证账号

```bash
python -m scripts.verify_accounts
```

### 5. 清理账号

```bash
python -m scripts.cleanup_accounts --status unhealthy
```

## 📋 脚本详细说明

### callback_server.py

OAuth 回调服务器，用于接收 OAuth 授权回调（默认后台运行）。

```bash
python -m scripts.callback_server [选项]

选项:
  -p, --port <端口>       监听端口 (默认: 1455)
  -f, --foreground        前台运行（调试用）

功能:
  - 监听 OAuth 回调 URL
  - 显示 code 和 state
  - 提供创建账号表单
```

### playwright_register.py

全自动Playwright自动化注册ChatGPT账号。

```bash
python -m scripts.playwright_register [选项]

选项:
  -c, --count <数量>      注册账号数量 (默认: 1)
  -e, --emails <邮箱>     DDG邮箱 (逗号分隔)
  -p, --passwords <密码>   DDG密码 (逗号分隔)
  -d, --delay <毫秒>      账号间延迟 (默认: 30000)
  --proxy <URL>           代理地址 (默认: http://127.0.0.1:7890)
  --no-proxy              不使用代理
  --no-headless           显示浏览器窗口

示例:
  python -m scripts.playwright_register -e "a@duck.com,b@duck.com" -p "Pass1,Pass2" -c 2
```

### verify_accounts.py

验证账号状态，检测异常账号。

```bash
python -m scripts.verify_accounts [选项]

选项:
  -n, --name <前缀>       验证指定账号
  -s, --status <状态>     状态筛选 (all/normal/limiting/error)
  --file <文件>           账号文件路径
  -o, --output <文件>      输出报告

示例:
  python -m scripts.verify_accounts
  python -m scripts.verify_accounts -n fresh-actor-branch
```

### cleanup_accounts.py

清理无效或异常的账号。

```bash
python -m scripts.cleanup_accounts [选项]

选项:
  -n, --name <前缀>       清理指定账号
  -s, --status <状态>     状态筛选 (unhealthy/disabled/all)
  -d, --dry-run           预览模式
  -y, --yes               跳过确认
  --file <文件>           账号文件路径

示例:
  python -m scripts.cleanup_accounts --status unhealthy
  python -m scripts.cleanup_accounts -n fresh-actor-branch --dry-run
```

### setup.py

交互式配置向导。

```bash
python -m scripts.setup
```

## ⚠️ 已废弃 (DEPRECATED)

以下内容已废弃，仅供存档参考：

- ❌ `batch-register.js`
- ❌ `batch_register.py`
- ❌ 所有CURL命令 → 使用 `scripts/api.py`

## 🔧 环境要求

- Python 3.10+
- requests >= 2.31.0
- rich >= 13.7.0
- playwright >= 1.40.0

## 📝 更新日志

### v7.0 (2026-03-22)

- ✅ 添加 callback_server.py OAuth 回调服务器
- ✅ 页面提供输入框输入 session_id 并创建账号
- ✅ 移除 --auto 和 --session CLI 参数

### v6.1 (2026-03-21)

- ✅ 删除 test_oauth.py
- ✅ 移除 login() 方法，统一使用 x-api-key 认证
- ✅ 移除 admin_email/admin_password 配置

### v6.0 (2026-03-21)

- ✅ 删除 batch_register.py（半自动版本）
- ✅ 保留 playwright_register.py（全自动版本）

### v5.0 (2026-03-20)

- ✅ 所有脚本转换为Python
- ✅ API客户端封装所有CURL命令
- ✅ 标记CURL命令和Node.js脚本为废弃
- ✅ 添加Rich库美化输出
