# photo/photo_capturer.py
"""
PhotoCapturer 主类，封装了拍照、分析、智能拍照等核心功能。
"""
import time
import camera  # type: ignore
from camera_driver import get_camera, capture_image
from flash import get_flash
from sd_card import get_sd_card
from .brightness_analyzer import capture_and_analyze_brightness
from .smart_capture_flow import run_smart_capture_flow
from config import debug_log, LEVEL_INFO, LEVEL_WARNING


def _debug_log(msg):
    debug_log(msg, module="PhotoCapturer")


class PhotoCapturer:
    """
    照片捕获器，提供基础拍照、带分析的拍照和智能拍照功能。

    Attributes:
        flash_pin (int): 闪光灯 GPIO 引脚号。
        flash_on_value (int): 点亮闪光灯的电平（1 或 0）。
        sd_mount_point (str): SD 卡挂载路径。
        camera_params (dict): 摄像头初始化参数（如 framesize, quality 等）。
    """

    def __init__(self, flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", camera_params=None):
        self.flash_pin = flash_pin
        self.flash_on_value = flash_on_value
        self.sd_mount_point = sd_mount_point
        self.camera_params = camera_params or {}
        _debug_log("PhotoCapturer initialized with params: {}".format(self.camera_params))

    def setup_camera(self, **kwargs):
        """
        根据提供的参数初始化摄像头（会先释放已有实例）。

        Args:
            **kwargs: 摄像头初始化参数，会与 self.camera_params 合并。
        """
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
        """
        拍摄一张照片（强制开启闪光灯）。

        Args:
            filename (str, optional): 保存的文件名（绝对路径），若 None 则自动生成。
            pre_flash_delay (int): 闪光灯开启后到拍摄的延时（毫秒）。
            post_flash_delay (int): 拍摄后闪光灯关闭前的延时（毫秒）。
            auto_deinit (bool): 拍摄结束后是否自动释放摄像头。

        Returns:
            str or None: 保存的文件路径，失败则返回 None。
        """
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
        """释放摄像头并关闭闪光灯。"""
        _debug_log("cleanup called")
        cam = get_camera()
        if cam.initialized:
            cam.deinit()
        flash = get_flash()
        flash.off()

    def capture_analysis(self, framesize=None, flash_off=True):
        """
        捕获并分析亮度（委托给 brightness_analyzer 模块）。

        Args:
            framesize (int, optional): 分析用分辨率。
            flash_off (bool): 分析时是否关闭闪光灯。

        Returns:
            dict or None: 分析结果。
        """
        return capture_and_analyze_brightness(self.camera_params, framesize, flash_off)

    def take_photo_with_analysis(self, filename=None, pre_flash_delay=200,
                                 post_flash_delay=0, auto_deinit=True):
        """
        先分析场景亮度，再拍照（仍强制开闪光灯）。

        Args:
            同 take_photo。

        Returns:
            tuple: (文件路径, 分析结果字典)
        """
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
        """
        智能拍照：自动分析亮度并决定是否开闪光灯，同时校验照片是否过暗。

        Args:
            filename (str): 保存文件名。
            quality (int): JPEG 质量。
            pre_flash_delay (int): 闪光灯预闪延时。
            retry_analysis_limit (int): 分析阶段最大重试次数。
            retry_capture_limit (int): 拍照阶段最大重试次数。
            brightness_threshold (float): 亮度阈值（低于此值认为过暗）。
            auto_deinit (bool): 完成后是否释放摄像头。

        Returns:
            str or None: 保存的文件路径。
        """
        return run_smart_capture_flow(
            capturer=self,
            filename=filename,
            quality=quality,
            pre_flash_delay=pre_flash_delay,
            retry_analysis_limit=retry_analysis_limit,
            retry_capture_limit=retry_capture_limit,
            brightness_threshold=brightness_threshold,
            auto_deinit=auto_deinit
        )


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    print("PhotoCapturer 测试（需硬件）")
    capturer = PhotoCapturer(camera_params={"framesize": camera.FRAME_VGA})
    # 模拟测试：仅打印方法存在性
    print("方法列表:", [m for m in dir(capturer) if not m.startswith("_")])