# utils/__init__.py
"""
utils - 通用工具包（纯算法，无硬件依赖）

本包提供与硬件无关的纯工具函数，包括：
    1. 亮度分析（analyze_brightness, quick_brightness_estimate）
    2. 图像信息提取（get_image_info, get_image_size, get_image_dimensions）
    3. 图像格式编码（encode_rgb565_to_bmp, encode_rgb565_to_ppm, encode_grayscale_to_pgm）
    4. 测试图像生成（create_uniform_image, create_gradient_image, ...）
    5. 文件加载（load_image_from_file）
    6. 设备信息报告（print_info, get_sd_info）

所有函数均为纯 Python 实现，不依赖任何硬件（machine, camera 等），
可在 PC 或 MicroPython 环境中直接使用。
"""

# ---------- 亮度分析 ----------
from .brightness import analyze_brightness, quick_brightness_estimate

# ---------- 图像元信息 ----------
from .image_info import get_image_info, get_image_size, get_image_dimensions

# ---------- 图像格式编码（新增） ----------
from .image_encoders import (
    encode_rgb565_to_bmp,
    encode_rgb565_to_ppm,
    encode_grayscale_to_pgm,
    encode_grayscale_to_raw,
)

# ---------- 测试图像生成 ----------
from .test_images import (
    create_uniform_image,
    create_gradient_image,
    create_checkerboard_image,
    create_center_bright_image,
    create_center_dark_image,
)

# ---------- 文件 I/O ----------
from .file_io import load_image_from_file

# ---------- 设备信息 ----------
from .device_info import print_info, get_sd_info

# ---------- 公共 API 列表（支持 from utils import *） ----------
__all__ = [
    # 亮度分析
    "analyze_brightness",
    "quick_brightness_estimate",

    # 图像元信息
    "get_image_info",
    "get_image_size",
    "get_image_dimensions",

    # 图像格式编码
    "encode_rgb565_to_bmp",
    "encode_rgb565_to_ppm",
    "encode_grayscale_to_pgm",
    "encode_grayscale_to_raw",

    # 测试图像生成
    "create_uniform_image",
    "create_gradient_image",
    "create_checkerboard_image",
    "create_center_bright_image",
    "create_center_dark_image",

    # 文件 I/O
    "load_image_from_file",

    # 设备信息
    "print_info",
    "get_sd_info",
]