# camera_driver/capture.py
"""
高级捕获函数

提供 JPEG 和 GRAYSCALE 格式的图像捕获功能。
所有函数捕获后自动释放摄像头资源。
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

    参数同 CameraController.init()。

    返回：
        bytes: JPEG 图像数据，失败返回 None。
    """
    cam = get_camera()
    if cam.initialized:
        _debug_log("capture_image: deinit existing camera")
        cam.deinit()
    _debug_log("capture_image: initializing camera...")
    cam.init(framesize=framesize, quality=quality, format=format,
             fb_location=fb_location, xclk_freq=xclk_freq,
             flip=flip, mirror=mirror, saturation=saturation,
             brightness=brightness, contrast=contrast,
             whitebalance=whitebalance, effect=effect)
    _debug_log("capture_image: capturing...")
    buf = cam.capture()
    cam.deinit()

    # 关键修复：统一返回 None 表示失败
    if buf is None or buf is False:
        _debug_log("capture_image: failed")
        return None

    _debug_log("capture_image: done, size={}".format(len(buf)))
    return buf

def capture_grayscale(framesize=camera.FRAME_XGA, quality=10,
                      flip=1, mirror=0, whitebalance=camera.WB_CLOUDY):
    """
    捕获一帧灰度图像。

    参数：
        framesize (int): 分辨率常量。
        quality (int): 仅用于兼容，灰度模式忽略。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。
        whitebalance (int): 白平衡模式。

    返回：
        bytes: 灰度图像数据（每像素 1 字节），失败返回 None。
    """
    cam = get_camera()
    if cam.initialized:
        _debug_log("capture_grayscale: deinit existing camera")
        cam.deinit()

    try:
        _debug_log("capture_grayscale: initializing camera in grayscale mode")
        cam.init(
            framesize=framesize,
            format=camera.GRAYSCALE,
            quality=quality,
            flip=flip,
            mirror=mirror,
            whitebalance=whitebalance,
        )
        _debug_log("capture_grayscale: capturing...")
        gray_buf = cam.capture()
        if gray_buf is None or gray_buf is False:
            _debug_log("capture_grayscale: capture failed")
            return None
        _debug_log("capture_grayscale: success, size={}".format(len(gray_buf)))
        return gray_buf
    except Exception as e:
        _debug_log("capture_grayscale: error: {}".format(e))
        return None
    finally:
        cam.deinit()
        _debug_log("capture_grayscale: camera released")