# camera_driver/controller.py
"""CameraController 类"""
import time
import camera  # type: ignore
from config import debug_log, LEVEL_INFO, LEVEL_WARNING
from .resolutions import get_resolution as _get_resolution, get_name_by_value as _get_name


def _debug_log(msg, level=LEVEL_INFO):
    debug_log(msg, level=level, module="CameraCtrl")


class CameraController:
    def __init__(self):
        self.initialized = False

    def init(self, framesize=camera.FRAME_XGA, quality=10,
             format=camera.JPEG, fb_location=camera.PSRAM,
             xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
             saturation=0, brightness=0, contrast=0,
             whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
        max_retries = 3
        retry_delay = 200

        # 记录请求的分辨率名称
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

        # 保存请求的帧大小（实际可能因内存限制被降级，但我们无法可靠获取，保留请求值）
        self.framesize = framesize
        self.initialized = True
        self.quality = quality

        # 尝试获取实际帧大小（仅用于记录，若失败则忽略）
        try:
            actual = camera.framesize(0)
            if actual != framesize:
                _debug_log("Note: camera driver may have adjusted framesize to {}".format(actual))
        except Exception as e:
            # 忽略错误，不影响功能
            _debug_log("Could not query actual framesize: {}".format(e), level=LEVEL_WARNING)

        _debug_log("Camera initialized with requested framesize={} ({}), quality={}".format(
            self.framesize, _get_name(self.framesize) or "unknown", quality))

    def capture(self):
        """捕获一帧，失败时立即返回 None（无重试）"""
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
        return _get_resolution(framesize)