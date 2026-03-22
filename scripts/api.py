"""Sub2API client - 使用 x-api-key 认证"""

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import requests

from state import get_state_manager


@dataclass
class GenerateAuthUrlResponse:
    session_id: str
    auth_url: str


@dataclass
class CreateAccountResponse:
    id: int
    name: str
    status: str


@dataclass
class Account:
    id: int
    name: str
    email: str
    status: str
    platform: str
    account_type: str
    capacity: str
    group: str
    schedule: str
    auto_forwarding: bool
    ws_mode: str


class Sub2APIError(Exception):
    """Sub2API error exception."""

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(f"[{code}] {message}" if code else message)


class Sub2APIClient:
    """Sub2API client for managing accounts."""

    def __init__(self, base_url: str, admin_api_key: str):
        self.base_url = base_url.rstrip("/")
        self.admin_api_key = admin_api_key
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers using x-api-key."""
        return {"x-api-key": self.admin_api_key}

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers()
        headers.update(kwargs.pop("headers", {}))

        try:
            response = self._session.request(method, url, headers=headers, **kwargs)

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    raise Sub2APIError(
                        message=error_data.get("message", "Unknown error"),
                        code=error_data.get("code"),
                        status_code=response.status_code,
                    )
                except json.JSONDecodeError:
                    response.raise_for_status()

            return response.json() if response.text else {}

        except requests.RequestException as e:
            raise Sub2APIError(f"Request failed: {e}") from e

    def generate_auth_url(self) -> GenerateAuthUrlResponse:
        """生成 OAuth 授权链接"""
        result = self._request("POST", "/api/v1/admin/openai/generate-auth-url")
        data = result.get("data", result)

        session_id = data.get("session_id") or data.get("sessionId")
        auth_url = data.get("auth_url") or data.get("authUrl")

        # 保存 session_id 到状态文件
        state_manager = get_state_manager()
        state_manager.set_session(session_id)
        state_manager.set_step("generate_auth_url")
        state_manager.add_log("generate_auth_url", "success", f"Session ID: {session_id}")

        return GenerateAuthUrlResponse(
            session_id=session_id,
            auth_url=auth_url,
        )

    def create_account_from_oauth(
        self, session_id: str, code: str, state: str, name: str, group_ids: list[int] | None = None
    ) -> CreateAccountResponse:
        """从 OAuth 回调参数创建账号"""
        data = {
            "session_id": session_id,
            "code": code,
            "state": state,
            "name": name,
            "group_ids": group_ids or [1],
        }
        result = self._request("POST", "/api/v1/admin/openai/create-from-oauth", json=data)
        resp_data = result.get("data", result)

        return CreateAccountResponse(
            id=resp_data.get("id", 0),
            name=resp_data.get("name", name),
            status=resp_data.get("status", "正常"),
        )

    def get_accounts(self) -> list[Account]:
        """获取所有账号"""
        response_data = self._request("GET", "/api/v1/admin/accounts")

        accounts: list[Account] = []

        data = (
            response_data.get("data", response_data)
            if isinstance(response_data, dict)
            else response_data
        )

        if not isinstance(data, list):
            return accounts

        for item_data in data:
            if not isinstance(item_data, dict):
                continue
            accounts.append(
                Account(
                    id=item_data.get("id", 0),
                    name=item_data.get("name", ""),
                    email=item_data.get("email", ""),
                    status=item_data.get("status", ""),
                    platform=item_data.get("platform", ""),
                    account_type=item_data.get("type", ""),
                    capacity=item_data.get("capacity", ""),
                    group=item_data.get("group", ""),
                    schedule=item_data.get("schedule", ""),
                    auto_forwarding=item_data.get("autoForwarding", True),
                    ws_mode=item_data.get("wsMode", "passthrough"),
                )
            )

        return accounts

    def get_account(self, account_id: int) -> Account | None:
        """获取指定账号"""
        result = self._request("GET", f"/api/v1/admin/accounts/{account_id}")

        if not result:
            return None

        return Account(
            id=result.get("id", 0),
            name=result.get("name", ""),
            email=result.get("email", ""),
            status=result.get("status", ""),
            platform=result.get("platform", ""),
            account_type=result.get("type", ""),
            capacity=result.get("capacity", ""),
            group=result.get("group", ""),
            schedule=result.get("schedule", ""),
            auto_forwarding=result.get("autoForwarding", True),
            ws_mode=result.get("wsMode", "passthrough"),
        )

    def delete_account(self, account_id: int) -> bool:
        """删除账号"""
        self._request("DELETE", f"/api/v1/admin/accounts/{account_id}")
        return True

    def find_account_by_email(self, email: str) -> Account | None:
        """通过邮箱查找账号"""
        accounts = self.get_accounts()
        for account in accounts:
            if email.lower() in account.email.lower():
                return account
        return None

    def is_email_registered(self, email: str) -> bool:
        """检查邮箱是否已注册"""
        return self.find_account_by_email(email) is not None

    def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            self._request("GET", "/api/v1/admin/accounts")
            return True
        except Sub2APIError:
            return False


def create_client(config) -> Sub2APIClient:
    """从配置对象创建客户端"""
    return Sub2APIClient(
        base_url=config.sub2api.base_url,
        admin_api_key=config.sub2api.admin_api_key,
    )


# ==================== 可靠性函数 ====================

import random


DDG_ADJECTIVES = [
    "fresh",
    "quick",
    "smart",
    "bright",
    "swift",
    "calm",
    "bold",
    "keen",
    "warm",
    "cool",
    "fast",
    "slow",
    "new",
    "old",
    "big",
    "small",
]
DDG_NOUNS = [
    "actor",
    "tree",
    "star",
    "wave",
    "stone",
    "bird",
    "fish",
    "moon",
    "leaf",
    "rain",
    "sun",
    "rock",
    "road",
    "lake",
    "hill",
    "field",
]
DDG_SUFFIXES = [
    "branch",
    "path",
    "field",
    "stream",
    "hill",
    "lake",
    "vale",
    "dale",
    "crest",
    "point",
    "ridge",
    "cove",
    "fall",
    "wood",
    "land",
]


def is_valid_duck_email(email: str) -> bool:
    """验证 DDG 邮箱格式是否有效"""
    pattern = r"^[a-z]+-[a-z]+-[a-z]+@duck\.com$"
    return bool(re.match(pattern, email.lower()))


def generate_ddg_email() -> str:
    """生成随机 DDG 邮箱"""
    adj = random.choice(DDG_ADJECTIVES)
    noun = random.choice(DDG_NOUNS)
    suffix = random.choice(DDG_SUFFIXES)
    return f"{adj}-{noun}-{suffix}@duck.com"


def generate_valid_ddg_email(max_attempts: int = 100) -> str:
    """生成格式有效的 DDG 邮箱"""
    for _ in range(max_attempts):
        email = generate_ddg_email()
        if is_valid_duck_email(email):
            return email
    raise ValueError(f"无法在{max_attempts}次尝试内生成有效DDG邮箱")


def is_email_available(client: Sub2APIClient, email: str) -> bool:
    """检查邮箱是否已注册"""
    accounts = client.get_accounts()
    email_lower = email.lower()
    return not any(email_lower in acc.email.lower() for acc in accounts)


def extract_verification_code(email_body: str) -> str | None:
    """从邮件正文中提取验证码"""
    patterns = [
        r"\b\d{6}\b",
        r"[A-Z0-9]{6}",
        r"verification code[:\s]*([A-Z0-9]{5,8})",
        r"code[:\s]*(\d{5,8})",
    ]

    for pattern in patterns:
        match = re.search(pattern, email_body, re.IGNORECASE)
        if match:
            code = match.group(1) if match.lastindex else match.group(0)
            if code and code.isdigit():
                return code.zfill(6)
            return code
    return None


def safe_register_account(
    client: Sub2APIClient,
    email: str,
    max_retries: int = 3,
) -> tuple[str, bool] | None:
    """安全检查邮箱可用性"""
    for attempt in range(max_retries):
        check_email = email if attempt == 0 else generate_valid_ddg_email()
        if is_email_available(client, check_email):
            return check_email, True
    return None
