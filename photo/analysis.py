# camera_driver/analysis.py
"""
摄像头数据分析模块

本模块提供从摄像头捕获灰度图像并进行亮度分析的功能。
它封装了 `capture_grayscale` 和 `analyze_brightness` 等函数，实现了从捕获到分析的完整流程。

包含三个主要函数：
    1. analyze_brightness_from_camera() - 捕获灰度图并进行完整的亮度分析（平均值、RMS对比度、中心亮度）
    2. quick_brightness_from_camera() - 捕获灰度图并使用 9 点快速估计平均亮度（极快）
    3. quick_brightness_with_jpeg() - 快速亮度估计 + JPEG 捕获组合

所有函数自动管理摄像头资源（捕获后释放），并输出日志（受 `config.DEBUG` 控制）。
"""
import math
import camera  # type: ignore
from camera_driver.capture import capture_grayscale, capture_image
from camera_driver.controller import CameraController
from utils.brightness import analyze_brightness, quick_brightness_estimate
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Analyzer")


def analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2):
    """
    从摄像头捕获一帧灰度图像，并进行完整的亮度分析。

    该函数会初始化摄像头（如果尚未初始化），捕获指定分辨率的灰度图，
    然后调用 `analyze_brightness` 计算平均亮度、RMS 对比度和中心区域亮度。
    捕获完成后自动释放摄像头资源。

    参数：
        framesize (int): 摄像头分辨率常量，指定捕获的灰度图分辨率。
            可选值包括 `camera.FRAME_QQVGA`、`camera.FRAME_QVGA`、`camera.FRAME_VGA`、
            `camera.FRAME_XGA` 等。值越大图像越清晰，但处理时间更长。
            默认 `camera.FRAME_XGA` (1024x768)。
        step (int): 采样步长，用于 `analyze_brightness` 函数。
            步长 2 表示每隔一个像素采样，可大幅提升速度（约4倍），但精度略有下降。
            推荐值 1~4，默认 2。

    返回：
        dict or None: 包含亮度统计信息的字典，结构为：
            {
                'average_brightness': float,  # 全局平均亮度 (0~255)
                'rms_contrast': float,        # RMS 对比度（标准差）
                'center_brightness': float,   # 中心 1/4 区域平均亮度
                'dynamic_range': int,         # 最大灰度与最小灰度之差
                'min': int,                   # 最小灰度值
                'max': int                    # 最大灰度值
            }
            若捕获或分析失败，返回 None。
    """
    _debug_log("Starting analysis with framesize={}, step={}".format(framesize, step))
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None
    _debug_log("Gray image size: {} bytes".format(len(gray_buf)))
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            w, h = 640, 480
        _debug_log("Inferred size: {}x{}".format(w, h))
    else:
        _debug_log("Resolution: {}x{}".format(w, h))
    result = analyze_brightness(gray_buf, w, h, step)
    if result:
        _debug_log("Analysis complete: avg={:.1f}, dynamic={}, center={:.1f}".format(
            result['average_brightness'], result['rms_contrast'], result['center_brightness']))
    return result


def quick_brightness_from_camera(framesize=camera.FRAME_XGA):
    """
    从摄像头捕获灰度图，并使用 9 点采样快速估计平均亮度。

    该函数仅读取图像中心区域 3×3 网格的 9 个像素，计算其平均值作为亮度估计。
    速度极快（微秒级），适用于需要快速判断环境光强弱的场景（如自动曝光决策）。

    参数：
        framesize (int): 分辨率常量，同 `analyze_brightness_from_camera`。
            建议使用较低分辨率（如 QVGA）以进一步加快速度。
            默认 `camera.FRAME_XGA`。

    返回：
        float or None: 9 个采样点的平均亮度（0~255），若失败返回 None。
    """
    _debug_log("Quick brightness estimation with framesize={}".format(framesize))
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None
    _debug_log("Gray image size: {} bytes".format(len(gray_buf)))
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            w, h = 640, 480
        _debug_log("Inferred size: {}x{}".format(w, h))
    else:
        _debug_log("Resolution: {}x{}".format(w, h))
    result = quick_brightness_estimate(gray_buf, w, h)
    if result is not None:
        _debug_log("Quick estimate: {:.1f}".format(result))
    return result


def quick_brightness_with_jpeg(framesize=camera.FRAME_XGA, quality=10):
    """
    快速亮度估计并捕获 JPEG 图像（组合函数）。

    先调用 `quick_brightness_from_camera` 估计亮度（灰度图），
    再捕获一张 JPEG 照片。返回亮度估计值和 JPEG 数据。

    参数：
        framesize (int): 分辨率常量，同时用于灰度估计和 JPEG 捕获。
            默认 `camera.FRAME_XGA`。
        quality (int): JPEG 质量，取值范围 10~63。
            数值越小画质越高（文件越大），反之画质越低（文件越小）。
            默认 10（高质量）。

    返回：
        tuple: (avg, jpeg_data)
            - avg (float or None): 快速亮度估计值（0~255），若失败为 None。
            - jpeg_data (bytes or None): JPEG 图像数据，若失败为 None。
    """
    _debug_log("Quick brightness with JPEG, framesize={}, quality={}".format(framesize, quality))
    avg = quick_brightness_from_camera(framesize)
    if avg is None:
        _debug_log("Brightness estimation failed, still trying to capture JPEG")
    _debug_log("Capturing JPEG image...")
    jpeg_data = capture_image(
        framesize=framesize,
        quality=quality,
        format=camera.JPEG,
        flip=1,
        mirror=0,
        whitebalance=camera.WB_CLOUDY
    )
    if jpeg_data is None:
        _debug_log("JPEG capture failed")
        return avg, None
    _debug_log("JPEG image size: {} bytes".format(len(jpeg_data)))
    return avg, jpeg_data