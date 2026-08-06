# photo_capturer.py
import camera
from flash import Flash
from camera_controller import CameraController
from sd_card import SDCardManager
import time


class PhotoCapturer:
    """
    集成闪光灯、摄像头和 SD 卡的拍照器类。
    提供一键拍照、带环境光分析的拍照、资源管理等功能。
    """

    def __init__(self, flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", camera_params=None):
        """
        初始化拍照器。

        参数：
            flash_pin (int): 闪光灯 GPIO 引脚，默认 4。
            flash_on_value (int): 闪光灯点亮电平，1 高电平，0 低电平。
            sd_mount_point (str): SD 卡挂载点，默认 "/sd"。
            camera_params (dict): 摄像头默认参数字典，可包含 framesize, quality, flip 等。
                                  若为 None 则使用空字典，后续在 setup_camera 中传入。
        """
        self.flash = Flash(pin=flash_pin, on_value=flash_on_value)
        self.sd = SDCardManager(mount_point=sd_mount_point)
        self.camera_params = camera_params or {}
        self.camera = None  # 摄像头控制器实例，延迟初始化

    def setup_camera(self, **kwargs):
        """
        初始化摄像头，使用默认参数并合并传入的覆盖参数。

        参数：
            **kwargs: 任意 CameraController.init() 支持的关键字参数，
                      会覆盖 self.camera_params 中的同名字段。
        """
        params = self.camera_params.copy()
        params.update(kwargs)
        self.camera = CameraController()
        self.camera.init(**params)

    def take_photo(self, filename=None, pre_flash_delay=200,
                   post_flash_delay=0, auto_deinit=True):
        """
        执行一次完整的拍照流程（打开闪光灯 -> 等待 -> 捕获 -> 关闭闪光灯 -> 保存）。
        无论捕获是否成功，闪光灯都会被强制关闭。

        参数：
            filename (str or None): 保存的文件名，若为 None 则自动生成时间戳文件名。
            pre_flash_delay (int): 开灯后等待曝光稳定的时间（毫秒），默认 200ms。
            post_flash_delay (int): 关灯后额外等待时间（毫秒），默认 0。
            auto_deinit (bool): 拍照完成后是否自动释放摄像头，默认 True。

        返回：
            str: 保存的文件完整路径；若失败则返回 None。
        """
        if self.camera is None:
            self.setup_camera()  # 使用默认参数初始化

        # 开启闪光灯
        self.flash.on()
        time.sleep_ms(pre_flash_delay)

        buf = None
        try:
            # 捕获图像（可能抛出异常）
            buf = self.camera.capture()
        except Exception as e:
            print("Capture exception:", e)
        finally:
            # 无论成功或异常，都关闭闪光灯
            self.flash.off()
            print("Flash turned off")

        if buf is None:
            print("Photo capture failed")
            if auto_deinit and self.camera:
                self.camera.deinit()
            return None

        if post_flash_delay:
            time.sleep_ms(post_flash_delay)

        # 保存文件
        try:
            filepath = self.sd.save_file(buf, filename)
        except Exception as e:
            print("Save error:", e)
            filepath = None

        if auto_deinit and self.camera:
            self.camera.deinit()

        return filepath

    def cleanup(self):
        """释放摄像头资源并强制关闭闪光灯（用于安全退出）。"""
        if self.camera and self.camera.initialized:
            self.camera.deinit()
        self.flash.off()

    # ---------- 图像分析辅助方法 ----------
    def _analyze_gray(self, gray_data, width, height):
        """
        分析灰度图像数据（私有方法）。

        参数：
            gray_data (bytes): 灰度图像数据。
            width (int): 图像宽度。
            height (int): 图像高度。

        返回：
            dict: 包含 average_brightness, dynamic_range, center_brightness, min, max。
        """
        if not gray_data:
            return None

        total = 0
        min_val = 255
        max_val = 0
        num_pixels = width * height

        # 中央区域（画面中心 1/4）
        center_x_start = width // 4
        center_x_end = width - center_x_start
        center_y_start = height // 4
        center_y_end = height - center_y_start
        center_sum = 0
        center_count = 0

        idx = 0
        for y in range(height):
            for x in range(width):
                val = gray_data[idx]
                total += val
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val
                if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                    center_sum += val
                    center_count += 1
                idx += 1

        avg = total / num_pixels
        dynamic = max_val - min_val
        center_avg = center_sum / center_count if center_count else avg

        return {
            "average_brightness": avg,
            "dynamic_range": dynamic,
            "center_brightness": center_avg,
            "min": min_val,
            "max": max_val,
        }

    def capture_analysis(self, framesize=None, flash_off=True):
        """
        捕获一帧灰度图像并分析环境亮度（闪光灯默认关闭）。

        参数：
            framesize (int or None): 指定分析时使用的分辨率，若为 None 则使用 self.camera_params 中的值。
            flash_off (bool): 是否关闭闪光灯，默认为 True。

        返回：
            dict: 分析结果（参见 _analyze_gray 返回值），失败返回 None。
        """
        if flash_off:
            self.flash.off()

        params = self.camera_params.copy()
        if framesize is not None:
            params["framesize"] = framesize
        params["format"] = camera.GRAYSCALE  # 强制灰度模式

        from camera_controller import CameraController
        gray_cam = CameraController()
        try:
            gray_cam.init(**params)
            gray_buf = gray_cam.capture()
            if gray_buf is None:
                print("Gray capture failed")
                return None
            w, h = CameraController.get_resolution(params.get("framesize", camera.FRAME_XGA))
            return self._analyze_gray(gray_buf, w, h)
        except Exception as e:
            print("Analysis error:", e)
            return None
        finally:
            gray_cam.deinit()

    def take_photo_with_analysis(self, filename=None, pre_flash_delay=200,
                                 post_flash_delay=0, auto_deinit=True):
        """
        先进行环境光分析（关闭闪光灯），再正常拍照（打开闪光灯）。

        返回：
            tuple: (保存路径, 分析结果字典)，路径为 None 表示拍照失败。
        """
        print("Analyzing scene...")
        analysis = self.capture_analysis(flash_off=True)
        if analysis:
            print("Analysis result:", analysis)
        else:
            print("Analysis skipped or failed")

        path = self.take_photo(
            filename=filename,
            pre_flash_delay=pre_flash_delay,
            post_flash_delay=post_flash_delay,
            auto_deinit=auto_deinit
        )
        return path, analysis