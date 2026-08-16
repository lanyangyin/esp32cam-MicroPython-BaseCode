# camera_driver/__init__.py
"""
摄像头驱动包

本包提供对 ESP32-CAM 摄像头的底层硬件抽象和控制。
它封装了 MicroPython 的 `camera` 模块，提供了单例管理、图像捕获、参数配置、
分辨率查询等功能，是上层拍照和视频应用的基础。

功能模块：
    - singleton: 摄像头单例管理（获取/重置）
    - capture: 高级图像捕获（JPEG/GRAYSCALE）
    - controller: 摄像头控制器类（初始化/参数设置/捕获/释放）
    - resolutions: 分辨率常量名称和尺寸映射
    - analysis: 基于摄像头捕获的亮度分析

典型用法：
    # 获取摄像头实例并初始化
    from camera_driver import get_camera
    cam = get_camera(framesize=camera.FRAME_XGA, quality=10)
    # 捕获 JPEG 图像
    jpeg = cam.capture()
    # 释放资源
    cam.deinit()

    # 直接使用高级捕获函数（自动管理资源）
    from camera_driver import capture_image, capture_grayscale
    img = capture_image(framesize=camera.FRAME_VGA)
    gray = capture_grayscale(framesize=camera.FRAME_QVGA)
"""
from .singleton import get_camera, reset_camera, is_camera_available
from .capture import capture_image, capture_grayscale
from .controller import CameraController
from .resolutions import get_resolution, get_name_by_value, list_resolutions
from photo.analysis import (
    analyze_brightness_from_camera,
    quick_brightness_from_camera,
    quick_brightness_with_jpeg,
)

__all__ = [
    "get_camera",
    "reset_camera",
    "is_camera_available",
    "capture_image",
    "capture_grayscale",
    "CameraController",
    "get_resolution",
    "get_name_by_value",
    "list_resolutions",
    "analyze_brightness_from_camera",
    "quick_brightness_from_camera",
    "quick_brightness_with_jpeg",
]