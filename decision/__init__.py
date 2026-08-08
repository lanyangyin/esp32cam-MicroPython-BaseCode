# decision/__init__.py
from .flash import (
    load_flash_guide,
    reload_flash_guide,
    evaluate_flash_decision,
    should_use_flash,
    get_recommended_settings,
)
from .retry import (
    load_retry_guide,
    reload_retry_guide,
    evaluate_retry_decision,
    should_retry,
    get_retry_reason,
    get_retry_action,
)
from .black_photo import is_black_photo
from .quick_flash import (
    load_quick_flash_guide,
    reload_quick_flash_guide,
    quick_should_use_flash,
    set_quick_flash_threshold,
)
from .flash_decision_helper import flash_decision_helper

__all__ = [
    # 原有导出
    "load_flash_guide",
    "reload_flash_guide",
    "evaluate_flash_decision",
    "should_use_flash",
    "get_recommended_settings",
    "load_retry_guide",
    "reload_retry_guide",
    "evaluate_retry_decision",
    "should_retry",
    "get_retry_reason",
    "get_retry_action",
    "is_black_photo",
    # 快速闪光灯
    "load_quick_flash_guide",
    "reload_quick_flash_guide",
    "quick_should_use_flash",
    "set_quick_flash_threshold",
    # 辅助工具
    "flash_decision_helper",
]