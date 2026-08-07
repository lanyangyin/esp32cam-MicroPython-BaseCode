# camera_driver/__init__.py
from .singleton import get_camera, reset_camera
from .capture import capture_image, capture_grayscale
from .controller import CameraController
from .resolutions import get_resolution, get_name_by_value, list_resolutions
# 新增导出
from .analysis import (
    analyze_brightness_from_camera,
    quick_brightness_from_camera,
    quick_brightness_with_jpeg,
)

__all__ = [
    "get_camera",
    "reset_camera",
    "capture_image",
    "capture_grayscale",
    "CameraController",
    "get_resolution",
    "get_name_by_value",
    "list_resolutions",
    "analyze_brightness_from_camera",   # 新增
    "quick_brightness_from_camera",    # 新增
    "quick_brightness_with_jpeg",      # 新增
]