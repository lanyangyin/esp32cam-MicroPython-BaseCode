# camera_driver/controller.py
"""CameraController 类"""
import time
import camera  # type: ignore
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[CameraCtrl] " + msg)

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
                _debug_log("camera.init failed: {}".format(e))
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
        self.initialized = True
        self.framesize = framesize
        self.quality = quality
        _debug_log("Camera initialized with framesize={}, quality={}".format(framesize, quality))

    def capture(self):
        if not self.initialized:
            raise RuntimeError("Camera not initialized")
        _debug_log("capture: calling camera.capture()")
        buf = camera.capture()
        if buf is None:
            _debug_log("capture: failed")
        else:
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
        res_map = {
            camera.FRAME_QQVGA: (160, 120),
            camera.FRAME_QVGA: (320, 240),
            camera.FRAME_VGA: (640, 480),
            camera.FRAME_XGA: (1024, 768),
            camera.FRAME_SVGA: (800, 600),
            camera.FRAME_UXGA: (1600, 1200),
        }
        return res_map.get(framesize, (640, 480))