# camera_driver/capture.py
"""
高级图像捕获函数

提供 JPEG 和 GRAYSCALE 格式的图像捕获功能。
这些函数自动管理摄像头资源的初始化和释放，调用后无需手动释放。

主要函数：
    - capture_image(): 捕获 JPEG 图像
    - capture_grayscale(): 捕获灰度图像（每像素 1 字节）

所有函数均支持自定义分辨率、质量、白平衡等参数，
并返回原始数据（bytes）或 None（失败时）。
"""
import camera  # type: ignore
from .singleton import get_camera
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="CameraCtrl")


def capture_image(framesize=camera.FRAME_XGA, quality=10,
                  format=camera.JPEG, fb_location=camera.PSRAM,
                  xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
                  saturation=0, brightness=0, contrast=0,
                  whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
    """
    捕获一帧 JPEG 图像。

    该函数会通过 `get_camera` 获取摄像头实例，并传入所有参数进行初始化，
    然后捕获 JPEG 照片，最后释放摄像头资源。

    参数：
        framesize (int): 图像分辨率常量，决定输出图像的大小。
            常用值：
                - camera.FRAME_QQVGA (160x120)
                - camera.FRAME_QVGA  (320x240)
                - camera.FRAME_VGA   (640x480)
                - camera.FRAME_XGA   (1024x768)
                - camera.FRAME_SVGA  (800x600)
                - camera.FRAME_UXGA  (1600x1200)
            默认 camera.FRAME_XGA。
        quality (int): JPEG 压缩质量，取值范围 10~63。
            数值越小画质越高（文件越大），默认 10（高质量）。
        format (int): 图像格式，固定为 `camera.JPEG`（无需修改）。
        fb_location (int): 帧缓冲区位置，`camera.PSRAM` 或 `camera.DRAM`。
            使用 PSRAM 可支持更高分辨率，默认 camera.PSRAM。
        xclk_freq (int): 摄像头主时钟频率，`camera.XCLK_10MHz` 或 `camera.XCLK_20MHz`。
            10MHz 更稳定，20MHz 可能提高帧率，默认 10MHz。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。
        saturation (int): 饱和度，取值范围 -2 ~ 2，0 为正常。
        brightness (int): 亮度，取值范围 -2 ~ 2，0 为正常。
        contrast (int): 对比度，取值范围 -2 ~ 2，0 为正常。
        whitebalance (int): 白平衡模式，常用值：
            - camera.WB_NONE (关闭)
            - camera.WB_SUNNY (晴天)
            - camera.WB_CLOUDY (阴天)
            - camera.WB_OFFICE (办公室/荧光灯)
            - camera.WB_HOME (室内)
            默认 camera.WB_CLOUDY。
        effect (int): 特殊效果，常用值：
            - camera.EFFECT_NONE (无)
            - camera.EFFECT_NEG (负片)
            - camera.EFFECT_BW (黑白)
            - camera.EFFECT_RED / GREEN / BLUE
            - camera.EFFECT_RETRO (复古)
            默认 EFFECT_NONE。

    返回：
        bytes or None: JPEG 图像数据（字节对象），若捕获失败返回 None。
    """
    # 直接通过 get_camera 传入参数进行初始化（如果已有实例则重新初始化）
    cam = get_camera(
        framesize=framesize,
        quality=quality,
        format=format,
        fb_location=fb_location,
        xclk_freq=xclk_freq,
        flip=flip,
        mirror=mirror,
        saturation=saturation,
        brightness=brightness,
        contrast=contrast,
        whitebalance=whitebalance,
        effect=effect
    )
    _debug_log("capture_image: capturing...")
    buf = cam.capture()
    # 释放摄像头资源（因为 capture_image 是独立调用，应该释放）
    cam.deinit()

    # 统一返回 None 表示失败（兼容 camera.capture() 返回 False 的情况）
    if buf is None or buf is False:
        _debug_log("capture_image: failed")
        return None

    _debug_log("capture_image: done, size={}".format(len(buf)))
    return buf


def capture_grayscale(framesize=camera.FRAME_XGA, quality=10,
                      flip=1, mirror=0, whitebalance=camera.WB_CLOUDY):
    """
    捕获一帧灰度图像（原始灰度数据，每像素 1 字节）。

    该函数以灰度模式初始化摄像头，捕获后自动释放资源。

    参数：
        framesize (int): 分辨率常量，同 `capture_image`。
        quality (int): 仅用于兼容，灰度模式通常忽略此参数（保留即可）。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。
        whitebalance (int): 白平衡模式，同 `capture_image` 中的说明。
            灰度图对白平衡不敏感，但可保留配置。

    返回：
        bytes or None: 灰度图像数据（每个像素一字节，0~255），若失败返回 None。
    """
    # 直接通过 get_camera 传入参数进行初始化（如果已有实例则重新初始化）
    cam = get_camera(
        framesize=framesize,
        quality=quality,
        format=camera.GRAYSCALE,
        flip=flip,
        mirror=mirror,
        whitebalance=whitebalance
    )
    _debug_log("capture_grayscale: capturing...")
    gray_buf = cam.capture()
    # 释放摄像头资源
    cam.deinit()

    if gray_buf is None or gray_buf is False:
        _debug_log("capture_grayscale: capture failed")
        return None
    _debug_log("capture_grayscale: success, size={}".format(len(gray_buf)))
    return gray_buf