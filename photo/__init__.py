# photo/__init__.py
"""
Photo 模块：提供各种拍照功能。
"""
from .photo_capturer import PhotoCapturer
from .smart_photo_taker import take_smart_photo
from .downgrade_capture import take_photo_with_downgrade
from .manual_photo_taker import take_photo_manual

__all__ = [
    "PhotoCapturer",
    "take_smart_photo",
    "take_photo_with_downgrade",
    "take_photo_manual",
]