"""Configuration loader for openai-ddg-account-registration."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OutlookConfig:
    email: str = ""
    password: str = ""
    login_url: str = "https://outlook.live.com/mail/junkemail"


@dataclass
class Sub2APIConfig:
    base_url: str = ""
    admin_api_key: str = ""


@dataclass
class DDGConfig:
    settings_url: str = "https://duckduckgo.com/email/settings/autofill"


@dataclass
class PersonalInfoConfig:
    full_name_pattern: str = "<FIRST> <LAST>"
    birthday_age_range: tuple[int, int] = (18, 60)


@dataclass
class DefaultsConfig:
    platform: str = "OpenAI"
    account_type: str = "OAuth ChatGPT OAuth"
    auto_forwarding: bool = True
    ws_mode: str = "passthrough"
    group: str = "OpenAI-Free"
    group_id: int = 1
    password_pattern: str = "TestPass{n}!@#"
    personal_info: PersonalInfoConfig = field(default_factory=PersonalInfoConfig)


@dataclass
class AdvancedConfig:
    max_retries: int = 3
    timeout_ms: int = 60000


@dataclass
class Config:
    outlook: OutlookConfig = field(default_factory=OutlookConfig)
    sub2api: Sub2APIConfig = field(default_factory=Sub2APIConfig)
    ddg: DDGConfig = field(default_factory=DDGConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)


def _dict_to_dataclass(data: dict[str, Any], cls: type) -> Any:
    """Convert a dictionary to a dataclass instance."""
    if not isinstance(data, dict):
        return data
    field_names = {f.name for f in cls.__dataclass_fields__.values()}
    filtered_data = {k: v for k, v in data.items() if k in field_names}

    kwargs = {}
    for key, value in filtered_data.items():
        field_type = cls.__dataclass_fields__[key].type
        if "PersonalInfoConfig" in str(field_type):
            kwargs[key] = _dict_to_dataclass(value, PersonalInfoConfig)
        elif "tuple" in str(field_type) and isinstance(value, list):
            kwargs[key] = tuple(value)
        else:
            kwargs[key] = value

    return cls(**kwargs)


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from JSON file."""
    if config_path is None:
        config_path = _find_config_file()

    if config_path is None or not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found. Please run setup or create: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = Config()

    if "outlook" in data:
        config.outlook = _dict_to_dataclass(data["outlook"], OutlookConfig)

    if "sub2api" in data:
        sub2api_data = data["sub2api"].copy()
        sub2api_data = _camel_to_snake_obj(sub2api_data)
        config.sub2api = Sub2APIConfig(**sub2api_data)

    if "ddg" in data:
        config.ddg = _dict_to_dataclass(data["ddg"], DDGConfig)

    if "defaults" in data:
        defaults_data = data["defaults"].copy()
        if "personalInfo" in defaults_data:
            defaults_data["personal_info"] = _camel_to_snake_obj(defaults_data.pop("personalInfo"))
        config.defaults = _dict_to_dataclass(defaults_data, DefaultsConfig)

    if "advanced" in data:
        config.advanced = _dict_to_dataclass(data["advanced"], AdvancedConfig)

    return config


def _camel_to_snake_obj(data: dict[str, Any]) -> dict[str, Any]:
    """Convert all keys in dict from camelCase to snake_case."""
    result = {}
    for key, value in data.items():
        snake_key = _camel_to_snake(key)
        if isinstance(value, dict):
            result[snake_key] = _camel_to_snake_obj(value)
        else:
            result[snake_key] = value
    return result


def _find_config_file() -> Path:
    """Find config file in standard locations."""
    locations = [
        Path.home() / "openai-sub2api-config.json",
        Path.home() / ".config" / "openai" / "openai-sub2api-config.json",
    ]

    for loc in locations:
        if loc.exists():
            return loc

    return locations[0]


def save_config(config: Config, config_path: str | Path | None = None) -> None:
    """Save configuration to JSON file."""
    if config_path is None:
        config_path = _find_config_file()

    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "outlook": {
            "email": config.outlook.email,
            "password": config.outlook.password,
            "loginUrl": config.outlook.login_url,
        },
        "sub2api": {
            "baseUrl": config.sub2api.base_url,
            "adminApiKey": config.sub2api.admin_api_key,
        },
        "ddg": {
            "settingsUrl": config.ddg.settings_url,
        },
        "defaults": {
            "platform": config.defaults.platform,
            "accountType": config.defaults.account_type,
            "autoForwarding": config.defaults.auto_forwarding,
            "wsMode": config.defaults.ws_mode,
            "group": config.defaults.group,
            "groupId": config.defaults.group_id,
            "passwordPattern": config.defaults.password_pattern,
            "personalInfo": {
                "fullNamePattern": config.defaults.personal_info.full_name_pattern,
                "birthdayAgeRange": list(config.defaults.personal_info.birthday_age_range),
            },
        },
        "advanced": {
            "maxRetries": config.advanced.max_retries,
            "timeoutMs": config.advanced.timeout_ms,
        },
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()
