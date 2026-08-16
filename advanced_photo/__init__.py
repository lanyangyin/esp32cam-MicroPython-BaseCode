# advanced_photo/__init__.py
"""
AdvancedPhoto 包：提供高级拍照和连拍功能。

本包扩展了基础 photo 模块，增加了自动闪光灯决策（基于亮度分析）、
黑照重试、连拍等功能。所有函数均提供丰富的参数配置，
并自动管理摄像头和闪光灯资源。

主要功能：
    - take_advanced_photo(): 单张高级拍照，支持多种闪光灯模式
    - burst_capture(): 连拍多张照片，返回总耗时
"""

from .advanced_capture import take_advanced_photo
from .burst_capture import burst_capture

__all__ = [
    "take_advanced_photo",
    "burst_capture",
]