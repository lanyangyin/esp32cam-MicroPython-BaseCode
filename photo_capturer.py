"""
photo_capturer.py - 高级拍照流程模块

本模块提供集成了闪光灯、摄像头和 SD 卡的高级拍照功能。
核心类 PhotoCapturer 封装了完整的拍照流程，包括环境光分析、闪光灯控制、
图像捕获和文件保存。

核心功能：
    1. 一键拍照：take_photo() - 开灯 -> 等待 -> 捕获 -> 关灯 -> 保存
    2. 分析+拍照：take_photo_with_analysis() - 先分析环境光，再拍照
    3. 环境光分析：capture_analysis() - 捕获灰度图并分析亮度
    4. 资源管理：cleanup() - 释放摄像头和闪光灯

设计特点：
    - 使用全局单例（flash、sd_card、camera），避免重复创建资源
    - 摄像头参数在初始化时配置，支持运行时覆盖
    - 闪光灯控制由本模块管理（开灯/关灯），确保正确时序
    - 灰度分析独立于拍照流程，可单独调用

依赖关系：
    - flash: 闪光灯单例
    - sd_card: SD 卡单例
    - camera_controller: 摄像头单例
    - config: 调试开关

典型用法：
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=1,
        camera_params={"framesize": camera.FRAME_XGA, "quality": 10}
    )
    saved_path = capturer.take_photo()
    capturer.cleanup()
"""
# photo_capturer.py
import time
import camera  # type: ignore
from flash import get_flash
from sd_card import get_sd_card
from camera_controller import get_camera, CameraController
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[PhotoCapturer] " + msg)

class PhotoCapturer:
    """
    集成闪光灯、摄像头和 SD 卡的拍照器类。
    使用全局单例对象，避免重复创建资源。
    提供一键拍照、带环境光分析的拍照、资源管理等功能。
    """

    def __init__(self, flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", camera_params=None):
        """
        初始化拍照器（只保存参数，不创建资源）。
        实际对象在首次使用时通过单例获取。

        参数：
            flash_pin (int): 闪光灯 GPIO 引脚，默认 4。
            flash_on_value (int): 闪光灯点亮电平，1 高电平，0 低电平。
            sd_mount_point (str): SD 卡挂载点，默认 "/sd"。
            camera_params (dict): 摄像头默认参数字典，可包含 framesize, quality, flip 等。
                                  若为 None 则使用空字典。
        """
        self.flash_pin = flash_pin
        self.flash_on_value = flash_on_value
        self.sd_mount_point = sd_mount_point
        self.camera_params = camera_params or {}
        _debug_log("PhotoCapturer initialized with params: {}".format(self.camera_params))

    def setup_camera(self, **kwargs):
        """
        初始化摄像头，使用默认参数并合并传入的覆盖参数。
        获取单例摄像头，若已初始化则先 deinit 再重新 init。
        """
        params = self.camera_params.copy()
        params.update(kwargs)
        _debug_log("setup_camera with params: {}".format(params))
        cam = get_camera()
        if cam.initialized:
            _debug_log("Deinitializing existing camera for setup")
            cam.deinit()
            time.sleep_ms(100)  # 等待硬件完全释放
        cam.init(**params)

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
        _debug_log("take_photo called, filename={}".format(filename))
        flash = get_flash(pin=self.flash_pin, on_value=self.flash_on_value)
        sd = get_sd_card(mount_point=self.sd_mount_point)
        cam = get_camera()

        if not cam.initialized:
            _debug_log("Camera not initialized, calling setup_camera with defaults")
            self.setup_camera()

        # 开闪光灯
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

        # 保存文件
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
        """释放摄像头资源并强制关闭闪光灯（用于安全退出）。"""
        _debug_log("cleanup called")
        cam = get_camera()
        if cam.initialized:
            cam.deinit()
        flash = get_flash()
        flash.off()

    # ---------- 图像分析辅助方法 ----------
    def _analyze_gray(self, gray_data, width, height):
        """分析灰度图像数据（私有方法），返回亮度统计字典。"""
        _debug_log("Analyzing gray image {}x{}".format(width, height))
        if not gray_data:
            return None
        total = 0
        min_val = 255
        max_val = 0
        num_pixels = width * height
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
        _debug_log("Analysis result: avg={:.1f}, dynamic={}, center={:.1f}".format(avg, dynamic, center_avg))
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
        """
        _debug_log("capture_analysis called, flash_off={}".format(flash_off))
        if flash_off:
            flash = get_flash()
            flash.off()
            _debug_log("Flash ensured OFF")

        params = self.camera_params.copy()
        if framesize is not None:
            params["framesize"] = framesize
        params["format"] = camera.GRAYSCALE

        cam = get_camera()
        if cam.initialized:
            _debug_log("Deinit camera for analysis")
            cam.deinit()
        try:
            _debug_log("Init camera for grayscale analysis")
            cam.init(**params)
            gray_buf = cam.capture()
            if gray_buf is None:
                _debug_log("Gray capture failed")
                return None
            w, h = CameraController.get_resolution(params.get("framesize", camera.FRAME_XGA))
            _debug_log("Got resolution: {}x{}".format(w, h))
            return self._analyze_gray(gray_buf, w, h)
        except Exception as e:
            _debug_log("Analysis error: {}".format(e))
            return None
        finally:
            cam.deinit()
            _debug_log("Camera released after analysis")

    def take_photo_with_analysis(self, filename=None, pre_flash_delay=200,
                                 post_flash_delay=0, auto_deinit=True):
        """
        先进行环境光分析（关闭闪光灯），再正常拍照（打开闪光灯）。
        """
        _debug_log("take_photo_with_analysis")
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

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    from camera_controller import reset_camera
    from flash import reset_flash
    from sd_card import reset_sd_card

    print("\n--- PhotoCapturer 模块测试 ---")
    # 清理所有资源
    reset_camera()
    reset_flash()
    reset_sd_card()
    time.sleep_ms(200)

    start = time.ticks_ms()

    # 创建实例
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=1,
        sd_mount_point="/sd",
        camera_params={
            "framesize": camera.FRAME_VGA,   # 使用较小分辨率加速
            "quality": 15,
            "flip": 1,
            "whitebalance": camera.WB_CLOUDY,
        }
    )

    # 测试仅拍照（使用临时文件名）
    test_filename = "test_photo_{}.jpg".format(time.time())
    print("测试拍照保存为: {}".format(test_filename))
    saved = capturer.take_photo(filename=test_filename, pre_flash_delay=100, auto_deinit=True)
    if saved:
        print("✅ 拍照成功:", saved)
        try:
            import uos
            uos.remove(saved)
            print("测试文件已删除")
        except Exception as e:
            print("删除测试文件失败:", e)
    else:
        print("❌ 拍照失败")

    # 测试分析+拍照
    print("\n测试分析+拍照...")
    test_filename2 = "test_analysis_{}.jpg".format(time.time())
    path2, analysis = capturer.take_photo_with_analysis(
        filename=test_filename2,
        pre_flash_delay=100,
        auto_deinit=True
    )
    if path2:
        print("✅ 分析+拍照成功:", path2)
        try:
            import uos
            uos.remove(path2)
            print("测试文件已删除")
        except:
            pass
        if analysis:
            print("分析结果:", analysis)
    else:
        print("❌ 分析+拍照失败")

    capturer.cleanup()
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))