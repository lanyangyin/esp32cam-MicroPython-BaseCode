# photo/capturer.py
"""PhotoCapturer 主类"""
import time
import camera  # type: ignore
from camera_driver import get_camera, capture_image
from flash import get_flash
from sd_card import get_sd_card
from .analyzers import capture_analysis
from .smart_flow import smart_capture_flow
from config import debug_log, LEVEL_INFO, LEVEL_WARNING


def _debug_log(msg):
    debug_log(msg, module="PhotoCapturer")

class PhotoCapturer:
    def __init__(self, flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", camera_params=None):
        self.flash_pin = flash_pin
        self.flash_on_value = flash_on_value
        self.sd_mount_point = sd_mount_point
        self.camera_params = camera_params or {}
        _debug_log("PhotoCapturer initialized with params: {}".format(self.camera_params))

    def setup_camera(self, **kwargs):
        params = self.camera_params.copy()
        params.update(kwargs)
        _debug_log("setup_camera with params: {}".format(params))
        cam = get_camera()
        if cam.initialized:
            _debug_log("Deinitializing existing camera for setup")
            cam.deinit()
            time.sleep_ms(100)
        cam.init(**params)

    def take_photo(self, filename=None, pre_flash_delay=200,
                   post_flash_delay=0, auto_deinit=True):
        _debug_log("take_photo called, filename={}".format(filename))
        flash = get_flash(pin=self.flash_pin, on_value=self.flash_on_value)
        sd = get_sd_card(mount_point=self.sd_mount_point)
        cam = get_camera()

        if not cam.initialized:
            _debug_log("Camera not initialized, calling setup_camera with defaults")
            self.setup_camera()

        _debug_log("Flash ON")
        flash.on()
        time.sleep_ms(pre_flash_delay)

        buf = None
        try:
            _debug_log("Capturing image...")
            buf = cam.capture()
        except Exception as e:
            _debug_log("Capture exception: {}".format(e))
        finally:
            flash.off()
            _debug_log("Flash OFF")

        if buf is None:
            _debug_log("Capture failed, no image data")
            if auto_deinit and cam.initialized:
                cam.deinit()
            return None

        if post_flash_delay:
            _debug_log("Post-flash delay {} ms".format(post_flash_delay))
            time.sleep_ms(post_flash_delay)

        try:
            _debug_log("Saving file...")
            filepath = sd.save_file(buf, filename)
            _debug_log("Saved to {}".format(filepath))
        except Exception as e:
            _debug_log("Save error: {}".format(e))
            filepath = None

        if auto_deinit and cam.initialized:
            _debug_log("Auto-deinit camera")
            cam.deinit()

        return filepath

    def cleanup(self):
        _debug_log("cleanup called")
        cam = get_camera()
        if cam.initialized:
            cam.deinit()
        flash = get_flash()
        flash.off()

    def capture_analysis(self, framesize=None, flash_off=True):
        """委托给 analyzers 模块"""
        return capture_analysis(self.camera_params, framesize, flash_off)

    # 在文件开头导入 LEVEL_INFO
    from config import debug_log, LEVEL_INFO

    # 在 take_photo_with_analysis 方法中：
    def take_photo_with_analysis(self, filename=None, pre_flash_delay=200,
                                 post_flash_delay=0, auto_deinit=True):
        _debug_log("take_photo_with_analysis")
        debug_log("Analyzing scene...", level=LEVEL_INFO, module="PhotoCapturer")
        analysis = self.capture_analysis(flash_off=True)
        if analysis:
            debug_log("Analysis result: {}".format(analysis), level=LEVEL_INFO, module="PhotoCapturer")
        else:
            debug_log("Analysis skipped or failed", level=LEVEL_WARNING, module="PhotoCapturer")
        path = self.take_photo(
            filename=filename,
            pre_flash_delay=pre_flash_delay,
            post_flash_delay=post_flash_delay,
            auto_deinit=auto_deinit
        )
        return path, analysis

    def smart_capture(self, filename=None, quality=10,
                      pre_flash_delay=200, retry_analysis_limit=6,
                      retry_capture_limit=5, brightness_threshold=2.5,
                      auto_deinit=True):
        """智能拍照：完全委托给 smart_flow 模块"""
        return smart_capture_flow(
            capturer=self,
            filename=filename,
            quality=quality,
            pre_flash_delay=pre_flash_delay,
            retry_analysis_limit=retry_analysis_limit,
            retry_capture_limit=retry_capture_limit,
            brightness_threshold=brightness_threshold,
            auto_deinit=auto_deinit
        )