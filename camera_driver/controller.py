# camera_driver/controller.py
"""
摄像头控制器类

提供 ESP32-CAM 摄像头的高级控制接口。
主要功能：
    - 初始化摄像头（支持重试机制）
    - 配置图像参数（分辨率、质量、白平衡、特效等）
    - 捕获单帧图像
    - 释放摄像头资源

设计上采用单例模式（由 `singleton.py` 管理），确保全局只有一个摄像头实例。
"""
import time
import camera  # type: ignore
from config import debug_log, LEVEL_INFO, LEVEL_WARNING
from .resolutions import get_resolution as _get_resolution, get_name_by_value as _get_name


def _debug_log(msg, level=LEVEL_INFO):
    debug_log(msg, level=level, module="CameraCtrl")


class CameraController:
    """
    ESP32-CAM 摄像头控制类。

    该类封装了 `camera` 模块的初始化和参数设置，提供了统一的重试机制和日志输出。
    通常不直接实例化，而是通过 `get_camera()` 获取单例。
    """

    def __init__(self):
        """初始化控制器，摄像头默认未初始化。"""
        self.initialized = False

    def init(self, framesize=camera.FRAME_XGA, quality=10,
             format=camera.JPEG, fb_location=camera.PSRAM,
             xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
             saturation=0, brightness=0, contrast=0,
             whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
        """
        初始化摄像头并应用图像参数。

        该方法会尝试初始化摄像头，若失败则重试（最多 3 次）。
        初始化成功后，应用所有图像调节参数（翻转、饱和度、白平衡等）。

        参数：
            framesize (int): 图像分辨率常量，控制输出图像尺寸。
                常用值见 `capture_image` 函数说明。
            quality (int): JPEG 质量，仅对 JPEG 格式有效，范围 10~63。
            format (int): 图像格式，`camera.JPEG`、`camera.GRAYSCALE`、`camera.RGB565` 等。
            fb_location (int): 帧缓冲区位置，`camera.PSRAM` 或 `camera.DRAM`。
            xclk_freq (int): 摄像头时钟频率，`camera.XCLK_10MHz` 或 `camera.XCLK_20MHz`。
            flip (int): 上下翻转，1 翻转，0 不翻转。
            mirror (int): 左右镜像，1 镜像，0 不镜像。
            saturation (int): 饱和度，-2 ~ 2。
            brightness (int): 亮度，-2 ~ 2。
            contrast (int): 对比度，-2 ~ 2。
            whitebalance (int): 白平衡模式，例如 `camera.WB_CLOUDY`。
            effect (int): 特效模式，例如 `camera.EFFECT_NONE`。

        异常：
            若初始化失败（包括重试后），抛出异常（`Exception`）。
        """
        max_retries = 3
        retry_delay = 200  # 毫秒

        req_name = _get_name(framesize) or str(framesize)
        _debug_log("Requested framesize: {} ({})".format(req_name, framesize))

        for attempt in range(max_retries):
            if self.initialized:
                _debug_log("init: deinit existing (attempt {})".format(attempt + 1))
                self.deinit()
                time.sleep_ms(50)
            _debug_log("init: calling camera.init() with framesize={} (attempt {})".format(framesize, attempt + 1))
            try:
                camera.init(0,
                            format=format,
                            fb_location=fb_location,
                            framesize=framesize,
                            xclk_freq=xclk_freq)
            except Exception as e:
                _debug_log("camera.init failed: {}".format(e), level=LEVEL_WARNING)
                try:
                    camera.deinit()
                except:
                    pass
                if attempt < max_retries - 1:
                    time.sleep_ms(retry_delay)
                    continue
                else:
                    raise
            else:
                break

        _debug_log("Applying image settings...")
        camera.flip(flip)
        camera.mirror(mirror)
        camera.saturation(saturation)
        camera.brightness(brightness)
        camera.contrast(contrast)
        camera.whitebalance(whitebalance)
        camera.speffect(effect)
        camera.quality(quality)

        self.framesize = framesize
        self.initialized = True
        self.quality = quality

        _debug_log("Camera initialized with requested framesize={} ({}), quality={}".format(
            self.framesize, _get_name(self.framesize) or "unknown", quality))

    def capture(self):
        """
        捕获一帧图像。

        该函数调用 `camera.capture()`，返回原始图像数据。
        如果摄像头未初始化，抛出 `RuntimeError`。

        返回：
            bytes or None: 图像数据（格式由 `init` 中的 `format` 决定），
                           若捕获失败返回 None。

        异常：
            RuntimeError: 摄像头未初始化时抛出。
        """
        if not self.initialized:
            raise RuntimeError("Camera not initialized")

        _debug_log("capture: calling camera.capture()")
        buf = camera.capture()
        if buf is None or buf is False:
            _debug_log("capture: failed")
            return None
        _debug_log("capture: success, size={}".format(len(buf)))
        return buf

    def deinit(self):
        """释放摄像头资源，关闭摄像头设备。"""
        if self.initialized:
            _debug_log("deinit: calling camera.deinit()")
            try:
                camera.deinit()
            except:
                pass
            self.initialized = False
            _debug_log("Camera deinitialized")

    @staticmethod
    def get_resolution(framesize):
        """
        根据分辨率常量返回对应的图像尺寸（宽, 高）。

        该静态方法委托给 `resolutions` 模块的统一映射表，避免重复定义。

        参数：
            framesize (int): 分辨率常量（如 `camera.FRAME_XGA`）。

        返回：
            tuple: (width, height)，若分辨率未知则返回 (None, None)。
        """
        return _get_resolution(framesize)