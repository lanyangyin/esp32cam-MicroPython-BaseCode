# photo/__init__.py
"""
Photo 模块：提供各种拍照功能。
"""
from .photo_capturer import PhotoCapturer
from .smart_photo_taker import take_smart_photo
from .downgrade_capture import take_photo_with_downgrade
from .manual_photo_taker import take_photo_manual
from .gray_quick import gray_quick_capture          # 新增
from .gray_analyzer import gray_analyzer_capture    # 新增

__all__ = [
    "PhotoCapturer",
    "take_smart_photo",
    "take_photo_with_downgrade",
    "take_photo_manual",
    "gray_quick_capture",
    "gray_analyzer_capture",
]