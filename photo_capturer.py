# photo_capturer.py
import camera  # ✅ 添加缺失的导入
from flash import Flash
from camera_controller import CameraController
from sd_card import SDCardManager
import time

class PhotoCapturer:
    """
    集成闪光灯、摄像头和 SD 卡，提供一键拍照保存功能。
    """
    def __init__(self, flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", camera_params=None):
        self.flash = Flash(pin=flash_pin, on_value=flash_on_value)
        self.sd = SDCardManager(mount_point=sd_mount_point)
        # 默认摄像头参数（可覆盖）
        self.camera_params = camera_params or {}
        self.camera = None

    def setup_camera(self, **kwargs):
        """初始化摄像头，可传入覆盖参数"""
        # 合并默认参数
        params = self.camera_params.copy()
        params.update(kwargs)
        self.camera = CameraController()
        self.camera.init(**params)

    def take_photo(self, filename=None, pre_flash_delay=200,
                   post_flash_delay=0, auto_deinit=True):
        """
        执行完整的拍照流程：
          1. 打开闪光灯
          2. 等待曝光稳定
          3. 捕获图像
          4. 关闭闪光灯（无论成功或异常都会执行）
          5. 保存到 SD 卡
        返回保存的文件路径，失败返回 None。
        """
        if self.camera is None:
            self.setup_camera()   # 使用默认参数

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
            # ✅ 关键：无论捕获是否成功或异常，都关闭闪光灯
            self.flash.off()
            print("Flash turned off")

        # 如果捕获失败，直接退出
        if buf is None:
            print("Photo capture failed")
            if auto_deinit and self.camera:
                self.camera.deinit()
            return None

        if post_flash_delay:
            time.sleep_ms(post_flash_delay)

        # 保存文件（如果保存异常，闪光灯已经关闭，不受影响）
        try:
            filepath = self.sd.save_file(buf, filename)
        except Exception as e:
            print("Save error:", e)
            filepath = None

        if auto_deinit and self.camera:
            self.camera.deinit()

        return filepath

    def cleanup(self):
        """释放所有资源，并强制关闭闪光灯"""
        if self.camera and self.camera.initialized:
            self.camera.deinit()
        self.flash.off()

    # ---------- 图像分析功能 ----------
    def _analyze_gray(self, gray_data, width, height):
        """
        分析灰度图像数据（bytes 或 bytearray），
        返回包含 average, dynamic_range, center_brightness 的字典。
        """
        if not gray_data:
            return None

        # 将 bytes 转换为可迭代的灰度值
        total = 0
        min_val = 255
        max_val = 0
        num_pixels = width * height

        # 中央区域定义：取画面中心 1/4 区域
        center_x_start = width // 4
        center_x_end = width - center_x_start
        center_y_start = height // 4
        center_y_end = height - center_y_start

        center_sum = 0
        center_count = 0

        # 遍历像素（注意 MicroPython 中 bytes 迭代返回 int）
        idx = 0
        for y in range(height):
            for x in range(width):
                val = gray_data[idx]
                total += val
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val

                # 判断是否在中央区域
                if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                    center_sum += val
                    center_count += 1

                idx += 1

        average = total / num_pixels
        dynamic_range = max_val - min_val
        center_brightness = center_sum / center_count if center_count else average

        return {
            "average_brightness": average,      # 0-255
            "dynamic_range": dynamic_range,     # 0-255
            "center_brightness": center_brightness,  # 0-255
            "min": min_val,
            "max": max_val,
        }

    def capture_analysis(self, framesize=None, flash_off=True):
        """
        捕获一帧灰度图像并分析环境亮度（闪光灯默认关闭）。
        返回分析结果字典，失败返回 None。
        """
        if flash_off:
            self.flash.off()  # 确保闪光灯关闭

        # 准备灰度摄像头参数
        params = self.camera_params.copy()
        if framesize is not None:
            params["framesize"] = framesize
        # 强制为灰度格式
        params["format"] = camera.GRAYSCALE

        # 临时创建灰度摄像头实例
        from camera_controller import CameraController
        gray_cam = CameraController()
        try:
            gray_cam.init(**params)
            gray_buf = gray_cam.capture()
            if gray_buf is None:
                print("Gray capture failed")
                return None

            # 获取分辨率
            w, h = CameraController.get_resolution(params.get("framesize", camera.FRAME_XGA))
            analysis = self._analyze_gray(gray_buf, w, h)
            return analysis
        except Exception as e:
            print("Analysis error:", e)
            return None
        finally:
            gray_cam.deinit()
            # 恢复闪光灯状态（如果原先开着？但拍照时会再开，这里无关紧要）

    def take_photo_with_analysis(self, filename=None, pre_flash_delay=200,
                                 post_flash_delay=0, auto_deinit=True):
        """
        先关闭闪光灯分析环境光，再正常拍照（打开闪光灯）。
        返回 (保存路径, 分析结果字典)，失败时路径为 None。
        """
        # 1. 环境光分析（不打开闪光灯）
        print("Analyzing scene...")
        analysis = self.capture_analysis(flash_off=True)
        if analysis:
            print("Analysis result:", analysis)
        else:
            print("Analysis skipped or failed")

        # 2. 正常拍照（打开闪光灯）
        path = self.take_photo(
            filename=filename,
            pre_flash_delay=pre_flash_delay,
            post_flash_delay=post_flash_delay,
            auto_deinit=auto_deinit
        )
        return path, analysis