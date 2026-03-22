"""
状态持久化管理

用于保存和恢复注册流程中的中间状态。
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class RegistrationState:
    """注册状态"""

    session_id: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    callback_code: Optional[str] = None
    callback_state: Optional[str] = None
    account_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class StateManager:
    """状态管理器"""

    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path(__file__).parent.parent / "state.json"
        self.state_file = state_file
        self.state: RegistrationState = self._load()

    def _load(self) -> RegistrationState:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return RegistrationState(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return RegistrationState()

    def _save(self):
        """保存状态到文件"""
        self.state.updated_at = datetime.now().isoformat()
        if self.state.created_at is None:
            self.state.created_at = self.state.updated_at

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)

    def set_session(self, session_id: str):
        """设置 session_id"""
        self.state.session_id = session_id
        self._save()

    def set_email(self, email: str, password: str):
        """设置邮箱和密码"""
        self.state.email = email
        self.state.password = password
        self._save()

    def set_name(self, name: str):
        """设置用户名"""
        self.state.name = name
        self._save()

    def set_callback(self, code: str, state: str):
        """设置回调信息"""
        self.state.callback_code = code
        self.state.callback_state = state
        self._save()

    def set_account(self, account_id: int):
        """设置账号ID"""
        self.state.account_id = account_id
        self.state.status = "completed"
        self._save()

    def set_status(self, status: str):
        """设置状态"""
        self.state.status = status
        self._save()

    def reset(self):
        """重置状态"""
        self.state = RegistrationState()
        if self.state_file.exists():
            self.state_file.unlink()

    def get(self) -> RegistrationState:
        """获取当前状态"""
        return self.state

    def is_completed(self) -> bool:
        """是否已完成"""
        return self.state.status == "completed"

    def has_callback(self) -> bool:
        """是否有回调信息"""
        return self.state.callback_code is not None and self.state.callback_state is not None


# 全局实例
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """获取状态管理器单例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
