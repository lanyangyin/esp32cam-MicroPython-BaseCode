# config/__init__.py
"""
配置管理包
统一导出调试开关、闪光灯配置、重拍配置等
"""
from .debug import DEBUG, set_debug
from .flash_config import (
    get_flash_guide_config,
    update_flash_guide_config,
    add_flash_rule,
    remove_flash_rule,
    get_flash_rule,
    list_flash_rules,
    reset_flash_guide,
)
from .retry_config import (
    get_retry_guide_config,
    update_retry_guide_config,
    add_retry_rule,
    remove_retry_rule,
    get_retry_rule,
    list_retry_rules,
    reset_retry_guide,
)

__all__ = [
    "DEBUG",
    "set_debug",
    "get_flash_guide_config",
    "update_flash_guide_config",
    "add_flash_rule",
    "remove_flash_rule",
    "get_flash_rule",
    "list_flash_rules",
    "reset_flash_guide",
    "get_retry_guide_config",
    "update_retry_guide_config",
    "add_retry_rule",
    "remove_retry_rule",
    "get_retry_rule",
    "list_retry_rules",
    "reset_retry_guide",
]