"""
状态持久化管理

用于保存和恢复注册流程中的中间状态。
"""

import json
import os
import portalocker
import tempfile
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: str
    step: str
    status: str  # success, failed, pending, retrying
    message: str


@dataclass
class AgentNotification:
    """Agent 通知信息"""

    status: str  # success, failed, pending
    message: str
    account_id: int | None
    timestamp: str


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

    # 新增字段
    current_step: str = ""
    error_message: str = ""
    logs: list = field(default_factory=list)  # list[LogEntry]
    agent_notification: Optional[dict] = None  # AgentNotification as dict


class StateManager:
    """状态管理器"""

    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path.cwd() / "state.json"
        self.state_file = state_file
        self.lock_file = state_file.with_suffix(".lock")
        self.lock_fd = None
        self.state: RegistrationState = self._load()

    def _acquire_lock(self, timeout: int = 10):
        """获取文件锁（带超时）"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_fd = open(self.lock_file, "w")
        deadline = time.monotonic() + timeout
        while True:
            try:
                portalocker.lock(self.lock_fd, portalocker.LOCK_EX)
                return
            except portalocker.LockException:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Could not acquire lock within {timeout}s")
                time.sleep(0.05)

    def _release_lock(self):
        """释放文件锁"""
        if self.lock_fd is None:
            return
        try:
            portalocker.unlock(self.lock_fd)
            self.lock_fd.close()
        except Exception:
            pass
        finally:
            self.lock_fd = None

    def _load(self) -> RegistrationState:
        """从文件加载状态（带读取锁）"""
        if not self.state_file.exists():
            return RegistrationState()

        self._acquire_lock()
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 处理 logs 字段
            if "logs" in data and isinstance(data["logs"], list):
                data["logs"] = [
                    LogEntry(**log) if isinstance(log, dict) else log for log in data["logs"]
                ]

            return RegistrationState(**data)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"State file corrupted: {e}")
        finally:
            self._release_lock()

    def _save(self):
        """原子写入状态文件（支持 Windows 重试）"""
        self.state.updated_at = datetime.now().isoformat()
        if self.state.created_at is None:
            self.state.created_at = self.state.updated_at

        self._acquire_lock()
        try:
            temp_file = self.state_file.with_suffix(".tmp")
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_file, "w", encoding="utf-8") as f:
                data = asdict(self.state)
                json.dump(data, f, indent=2, ensure_ascii=False)

            max_replace_retries = 3
            for attempt in range(max_replace_retries):
                try:
                    temp_file.replace(self.state_file)
                    break
                except OSError as e:
                    if attempt < max_replace_retries - 1:
                        time.sleep(0.1)
                    else:
                        raise e
        finally:
            self._release_lock()

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

    def add_log(self, step: str, status: str, message: str):
        """添加日志"""
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(), step=step, status=status, message=message
        )
        self.state.logs.append(log_entry)
        self._save()

    def set_step(self, step: str):
        """设置当前步骤"""
        self.state.current_step = step
        self._save()

    def set_error(self, message: str):
        """设置错误信息"""
        self.state.error_message = message
        self._save()

    def set_agent_notification(self, status: str, message: str, account_id: int | None = None):
        """设置 Agent 通知"""
        self.state.agent_notification = {
            "status": status,
            "message": message,
            "account_id": account_id,
            "timestamp": datetime.now().isoformat(),
        }
        self._save()

    def get_agent_notification(self) -> dict | None:
        """获取 Agent 通知"""
        return self.state.agent_notification

    def set_credentials(self, email: str, password: str, name: str):
        """设置凭证信息"""
        self.state.email = email
        self.state.password = password
        self.state.name = name
        self._save()

    def cleanup_expired(self, ttl_hours: int = 24):
        """清理过期状态文件"""
        if not self.state_file.exists():
            return

        try:
            mtime = datetime.fromtimestamp(self.state_file.stat().st_mtime)
            age_hours = (datetime.now() - mtime).total_seconds() / 3600

            if age_hours > ttl_hours:
                self.state_file.unlink()
                if self.lock_file.exists():
                    self.lock_file.unlink()
                self.state = RegistrationState()
                print(f"Cleaned up expired state file (age: {age_hours:.1f} hours)")
        except Exception as e:
            print(f"Warning: Failed to cleanup expired state file: {e}")

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
