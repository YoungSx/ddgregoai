"""
OAuth 回调服务器

功能：
1. 从启动起就一直运行在后台
2. 接收 OAuth 回调时，从 URL 提取 code 和 state
3. 在页面显示提取的 code 和 state，方便 Agent 直接复制使用
4. 用户可在页面上输入 session_id，点击按钮自动创建账号

使用方法：
    python scripts/callback_server.py

启动后会一直运行，直到手动停止 (Ctrl+C)
"""

import http.server
import urllib.parse
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from api import Sub2APIClient
from config import load_config


@dataclass
class CallbackData:
    code: str
    state: str
    timestamp: str
    session_id: Optional[str] = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    callback_data: Optional[CallbackData] = None

    def log_message(self, format, *args):
        print(f"[Callback] {format % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 处理创建账号请求
        if parsed.path == "/create" and params.get("session_id"):
            self._handle_create(params)
            return

        code = params.get("code", [""])[0]
        state = params.get("state", [""])[0]

        if not code:
            self.send_error(400, "Missing code parameter")
            return

        CallbackHandler.callback_data = CallbackData(
            code=code,
            state=state,
            timestamp=datetime.now().isoformat(),
        )

        print("\n" + "=" * 60)
        print("🔔 OAuth 回调已接收!")
        print("=" * 60)
        print(f"📋 Code:  {code[:50]}...")
        print(f"🔐 State: {state[:50]}...")
        print("=" * 60)

        html = self._generate_html(code, state)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _handle_create(self, params):
        """处理创建账号请求"""
        session_id = params.get("session_id", [""])[0]
        name = params.get("name", ["User"])[0]

        if not CallbackHandler.callback_data:
            self._send_json({"success": False, "error": "No callback data received"})
            return

        try:
            config = load_config()
            client = Sub2APIClient(
                base_url=config.sub2api.base_url, admin_api_key=config.sub2api.admin_api_key
            )

            print(f"\n正在创建账号 (session: {session_id[:30]}...)...")
            result = client.create_account_from_oauth(
                session_id=session_id,
                code=CallbackHandler.callback_data.code,
                state=CallbackHandler.callback_data.state,
                name=name,
                group_ids=[config.defaults.group_id],
            )

            print(f"✅ 账号创建成功! ID={result.id}, Name={result.name}")
            self._send_json(
                {
                    "success": True,
                    "account_id": result.id,
                    "name": result.name,
                    "status": result.status,
                }
            )

        except Exception as e:
            print(f"❌ 创建账号失败: {e}")
            self._send_json({"success": False, "error": str(e)})

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _generate_html(self, code: str, state: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OAuth 回调</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .success-icon {{
            text-align: center;
            font-size: 64px;
            margin-bottom: 20px;
        }}
        .field {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .field-label {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        .field-value {{
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            word-break: break-all;
            color: #333;
            background: #e9ecef;
            padding: 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .field-value:hover {{
            background: #dee2e6;
        }}
        .copy-hint {{
            color: #667eea;
            font-size: 12px;
            margin-top: 4px;
        }}
        .info {{
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 14px;
        }}
        .create-section {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }}
        .create-section h3 {{
            color: #333;
            margin-bottom: 16px;
            font-size: 16px;
        }}
        .input-group {{
            margin-bottom: 16px;
        }}
        .input-group label {{
            display: block;
            color: #666;
            font-size: 12px;
            margin-bottom: 6px;
        }}
        .input-group input {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 14px;
            transition: border-color 0.2s;
            font-family: 'Monaco', 'Menlo', monospace;
        }}
        .input-group input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .create-btn {{
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .create-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        .create-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        .result {{
            margin-top: 16px;
            padding: 16px;
            border-radius: 10px;
            text-align: center;
            display: none;
        }}
        .result.success {{
            background: #d4edda;
            color: #155724;
            display: block;
        }}
        .result.error {{
            background: #f8d7da;
            color: #721c24;
            display: block;
        }}
        .result.loading {{
            background: #cce5ff;
            color: #004085;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>OAuth 回调成功!</h1>
        
        <div class="field">
            <div class="field-label">Code</div>
            <div class="field-value" onclick="copyToClipboard(this)" title="点击复制">
                {code}
            </div>
            <div class="copy-hint">点击复制</div>
        </div>
        
        <div class="field">
            <div class="field-label">State</div>
            <div class="field-value" onclick="copyToClipboard(this)" title="点击复制">
                {state}
            </div>
            <div class="copy-hint">点击复制</div>
        </div>
        
        <div class="create-section">
            <h3>🚀 创建 Sub2API 账号</h3>
            <div class="input-group">
                <label>Session ID (从注册流程中获取)</label>
                <input type="text" id="sessionId" placeholder="输入 session_id...">
            </div>
            <div class="input-group">
                <label>用户名 (可选)</label>
                <input type="text" id="userName" placeholder="User">
            </div>
            <button class="create-btn" id="createBtn" onclick="createAccount()">
                创建账号
            </button>
            <div class="result" id="result"></div>
        </div>
    </div>
    
    <script>
        function copyToClipboard(element) {{
            navigator.clipboard.writeText(element.textContent.trim()).then(() => {{
                const original = element.textContent;
                element.textContent = '已复制!';
                element.style.background = '#667eea';
                element.style.color = 'white';
                setTimeout(() => {{
                    element.textContent = original;
                    element.style.background = '#e9ecef';
                    element.style.color = '#333';
                }}, 1500);
            }});
        }}
        
        async function createAccount() {{
            const sessionId = document.getElementById('sessionId').value.trim();
            const userName = document.getElementById('userName').value.trim() || 'User';
            const btn = document.getElementById('createBtn');
            const result = document.getElementById('result');
            
            if (!sessionId) {{
                result.className = 'result error';
                result.textContent = '请输入 Session ID';
                return;
            }}
            
            btn.disabled = true;
            btn.textContent = '创建中...';
            result.className = 'result loading';
            result.textContent = '正在创建账号...';
            
            try {{
                const response = await fetch(`/create?session_id=${{encodeURIComponent(sessionId)}}&name=${{encodeURIComponent(userName)}}`);
                const data = await response.json();
                
                if (data.success) {{
                    result.className = 'result success';
                    result.innerHTML = `✅ 账号创建成功!<br>ID: ${{data.account_id}}<br>Name: ${{data.name}}<br>Status: ${{data.status}}`;
                    btn.textContent = '已创建';
                }} else {{
                    result.className = 'result error';
                    result.textContent = '❌ 创建失败: ' + data.error;
                    btn.disabled = false;
                    btn.textContent = '重试';
                }}
            }} catch (e) {{
                result.className = 'result error';
                result.textContent = '❌ 请求失败: ' + e.message;
                btn.disabled = false;
                btn.textContent = '重试';
            }}
        }}
    </script>
</body>
</html>"""


class ReusableTCPServer(http.server.HTTPServer):
    """允许端口重用的服务器"""

    allow_reuse_address = True


def run_server(port: int = 1455):
    """运行回调服务器"""
    server = ReusableTCPServer(("localhost", port), CallbackHandler)

    print(f"""
╔════════════════════════════════════════════════════════════╗
║           🎯 OAuth 回调服务器                             ║
╠════════════════════════════════════════════════════════════╣
║  URL: http://localhost:{port}                            ║
║  模式: 手动输入 session_id 创建账号                       ║
╠════════════════════════════════════════════════════════════╣
║  等待 OAuth 回调...                                      ║
║  按 Ctrl+C 停止服务器                                    ║
╚════════════════════════════════════════════════════════════╝
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        server.shutdown()


def start_background(port: int = 1455):
    """在后台启动服务器，返回端口"""
    import threading

    def run():
        run_server(port)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    print(f"回调服务器已在后台启动 (端口 {port})")
    return port


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OAuth 回调服务器")
    parser.add_argument("-p", "--port", type=int, default=1455, help="监听端口 (默认: 1455)")
    parser.add_argument("-f", "--foreground", action="store_true", help="前台运行（调试用）")

    args = parser.parse_args()

    if args.foreground:
        run_server(args.port)
    else:
        start_background(args.port)
