"""
photo_capturer.py - 高级拍照流程模块

本模块提供集成了闪光灯、摄像头和 SD 卡的高级拍照功能。
核心类 PhotoCapturer 封装了完整的拍照流程，包括环境光分析、闪光灯控制、
图像捕获和文件保存。

核心功能：
    1. 一键拍照：take_photo() - 开灯 -> 等待 -> 捕获 -> 关灯 -> 保存
    2. 分析+拍照：take_photo_with_analysis() - 先分析环境光，再拍照
    3. 环境光分析：capture_analysis() - 捕获灰度图并分析亮度
    4. 智能拍照：smart_capture() - 自动重试、闪光灯决策、质量评估
    5. 资源管理：cleanup() - 释放摄像头和闪光灯

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
    - utils: 提供亮度分析函数
    - retry_decision: 重拍决策
    - flash_decision: 闪光灯决策

典型用法：
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=1,
        camera_params={"framesize": camera.FRAME_XGA, "quality": 10}
    )
    saved_path = capturer.smart_capture()
    capturer.cleanup()
"""
import time

import camera  # type: ignore

from camera_controller import get_camera, CameraController, capture_grayscale, capture_image
from config import DEBUG
from flash import get_flash
from flash_decision import should_use_flash
from retry_decision import should_retry
from sd_card import get_sd_card
from utils import analyze_brightness, quick_brightness_estimate


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

    # ---------- 新增：智能拍照 ----------
    def smart_capture(self, filename=None, quality=10,
                      pre_flash_delay=200, retry_analysis_limit=6,
                      retry_capture_limit=5, brightness_threshold=2.5,
                      auto_deinit=True):
        """
        智能拍照：自动进行亮度分析、重试、闪光灯决策，确保获得合格照片。

        流程：
            1. 预分析阶段（最多 retry_analysis_limit 次）：
               - 捕获灰度图，获取完整亮度信息（avg, dynamic, center）
               - 调用 retry_decision 判断是否需要重新获取亮度信息
               - 若不需要，则跳出循环；否则继续
               - 若循环结束，使用最后一次的亮度信息

            2. 闪光灯决策：根据最终亮度信息决定是否开启闪光灯

            3. 拍照阶段（最多 retry_capture_limit 次）：
               - 若需要闪光灯则开启，否则保持关闭
               - 捕获灰度图（反映当前光照条件），快速估计亮度
               - 若亮度 > brightness_threshold，则拍摄 JPEG 并保存，退出循环
               - 若亮度 <= threshold，则继续循环
               - 若循环结束，则最后拍摄一张 JPEG 保存（即使亮度低）

        参数：
            filename (str): 保存的文件名，若为 None 则自动生成。
            quality (int): JPEG 质量（10~63），默认 10。
            pre_flash_delay (int): 开灯后等待曝光稳定的时间（毫秒），默认 200。
            retry_analysis_limit (int): 预分析阶段最大重试次数，默认 6。
            retry_capture_limit (int): 拍照阶段最大重试次数，默认 5。
            brightness_threshold (float): 亮度阈值，默认 2.5。
            auto_deinit (bool): 完成后是否自动释放摄像头，默认 True。

        返回：
            str: 保存的文件路径，若失败返回 None。
        """
        # 1. 初始化闪光灯和 SD 卡（放在最前面，确保后续可用）
        _debug_log("smart_capture called, filename={}".format(filename))
        print("\n[智能拍照] 启动...")

        flash = get_flash(pin=self.flash_pin, on_value=self.flash_on_value)
        sd = get_sd_card(mount_point=self.sd_mount_point)

        # 2. 预分析阶段（关闭闪光灯进行）
        _debug_log("=== 预分析阶段（最多 {} 次）===".format(retry_analysis_limit))
        final_brightness = None

        for attempt in range(1, retry_analysis_limit + 1):
            _debug_log("预分析尝试 {}/{}".format(attempt, retry_analysis_limit))
            print("  预分析 {}/{}...".format(attempt, retry_analysis_limit))

            # 关闭闪光灯
            flash.off()

            # 捕获灰度图
            gray_buf = capture_grayscale(
                framesize=self.camera_params.get("framesize", camera.FRAME_XGA),
                whitebalance=camera.WB_CLOUDY
            )
            if gray_buf is None:
                _debug_log("灰度捕获失败，重试")
                continue

            # 获取分辨率
            framesize = self.camera_params.get("framesize", camera.FRAME_XGA)
            w, h = CameraController.get_resolution(framesize)
            if w is None or h is None:
                import math
                total = len(gray_buf)
                w = int(math.sqrt(total * 4 / 3))
                h = total // w
                if w * h != total:
                    w, h = 640, 480

            # 完整亮度分析
            brightness_info = analyze_brightness(gray_buf, w, h, step=2)
            if brightness_info is None:
                _debug_log("亮度分析失败，重试")
                continue

            _debug_log("亮度信息: avg={:.1f}, dynamic={}, center={:.1f}".format(
                brightness_info['average_brightness'],
                brightness_info['dynamic_range'],
                brightness_info['center_brightness']
            ))

            # 判断是否需要重新获取亮度信息
            if should_retry(brightness_info):
                _debug_log("触发重拍（亮度信息异常），继续预分析")
                if attempt == retry_analysis_limit:
                    print("  预分析达到最大次数，使用最后一次亮度信息")
                    final_brightness = brightness_info
                continue
            else:
                _debug_log("亮度信息正常，预分析完成")
                final_brightness = brightness_info
                break

        # 如果循环结束仍未得到有效亮度，使用保守默认
        if final_brightness is None:
            _debug_log("预分析全部失败，使用保守默认亮度（avg=0）")
            final_brightness = {"average_brightness": 0, "dynamic_range": 0, "center_brightness": 0}

        # 3. 闪光灯决策
        need_flash = should_use_flash(final_brightness)
        _debug_log("闪光灯决策: {}".format("需要" if need_flash else "不需要"))
        print("  闪光灯: {}".format("✅ 开启" if need_flash else "❌ 关闭"))

        # 4. 拍照阶段
        _debug_log("=== 拍照阶段（最多 {} 次）===".format(retry_capture_limit))
        jpeg_data = None
        final_path = None

        for attempt in range(1, retry_capture_limit + 1):
            _debug_log("拍照尝试 {}/{}".format(attempt, retry_capture_limit))
            print("  拍照 {}/{}...".format(attempt, retry_capture_limit))

            # 控制闪光灯
            if need_flash:
                flash.on()
                time.sleep_ms(pre_flash_delay)
                _debug_log("闪光灯已开启")
            else:
                flash.off()
                _debug_log("闪光灯已关闭")

            # 捕获灰度图（用于亮度评估）
            gray_buf = capture_grayscale(
                framesize=self.camera_params.get("framesize", camera.FRAME_XGA),
                whitebalance=camera.WB_CLOUDY
            )
            if gray_buf is None:
                _debug_log("灰度捕获失败，重试")
                continue

            # 获取尺寸
            w, h = CameraController.get_resolution(self.camera_params.get("framesize", camera.FRAME_XGA))
            if w is None or h is None:
                import math
                total = len(gray_buf)
                w = int(math.sqrt(total * 4 / 3))
                h = total // w
                if w * h != total:
                    w, h = 640, 480

            # 快速亮度估计
            est_avg = quick_brightness_estimate(gray_buf, w, h)
            if est_avg is None:
                _debug_log("快速估计失败，重试")
                continue

            _debug_log("快速估计亮度: {:.1f}".format(est_avg))
            print("    亮度估计: {:.1f} (阈值 {:.1f})".format(est_avg, brightness_threshold))

            # 判断亮度是否合格
            if est_avg > brightness_threshold:
                _debug_log("亮度合格，拍摄 JPEG")
                print("    ✅ 亮度合格，正在保存照片...")

                # 拍摄 JPEG（保持当前闪光灯状态）
                if need_flash:
                    flash.on()
                    time.sleep_ms(pre_flash_delay)
                else:
                    flash.off()

                jpeg_data = capture_image(
                    framesize=self.camera_params.get("framesize", camera.FRAME_XGA),
                    quality=quality,
                    format=camera.JPEG,
                    flip=self.camera_params.get("flip", 1),
                    mirror=self.camera_params.get("mirror", 0),
                    whitebalance=camera.WB_CLOUDY
                )
                flash.off()  # 拍摄后关闭

                if jpeg_data is None:
                    _debug_log("JPEG 捕获失败，重试")
                    continue

                # 保存文件
                if filename is None:
                    import time
                    filename = "smart_photo_{}.jpg".format(time.time())
                if not filename.startswith(self.sd_mount_point):
                    filename = self.sd_mount_point + "/" + filename.lstrip("/")

                try:
                    with open(filename, "wb") as f:
                        f.write(jpeg_data)
                    final_path = filename
                    _debug_log("照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
                    print("  ✅ 照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
                    break
                except Exception as e:
                    _debug_log("保存失败: {}".format(e))
                    print("  ❌ 保存失败: {}".format(e))
                    final_path = None
                    break
            else:
                _debug_log("亮度偏低，继续重试")
                print("    ❌ 亮度偏低，继续重试...")
                flash.off()

        # 如果循环结束仍未保存成功，强制保存一张
        if final_path is None:
            _debug_log("拍照阶段结束，未保存任何照片，尝试最后一次保存")
            print("  ⚠️ 所有尝试均未合格，保存最后一次 JPEG...")

            if need_flash:
                flash.on()
                time.sleep_ms(pre_flash_delay)
            else:
                flash.off()

            jpeg_data = capture_image(
                framesize=self.camera_params.get("framesize", camera.FRAME_XGA),
                quality=quality,
                format=camera.JPEG,
                flip=self.camera_params.get("flip", 1),
                mirror=self.camera_params.get("mirror", 0),
                whitebalance=camera.WB_CLOUDY
            )
            flash.off()

            if jpeg_data is not None:
                if filename is None:
                    import time
                    filename = "smart_photo_fallback_{}.jpg".format(time.time())
                if not filename.startswith(self.sd_mount_point):
                    filename = self.sd_mount_point + "/" + filename.lstrip("/")
                try:
                    with open(filename, "wb") as f:
                        f.write(jpeg_data)
                    final_path = filename
                    _debug_log("备用照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
                    print("  ✅ 备用照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
                except Exception as e:
                    _debug_log("备用保存失败: {}".format(e))
                    print("  ❌ 备用保存失败: {}".format(e))

        # 释放摄像头
        if auto_deinit:
            cam = get_camera()
            if cam.initialized:
                cam.deinit()
                _debug_log("摄像头已释放")

        print("[智能拍照] 完成")
        return final_path


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

    # 测试智能拍照
    print("\n--- 测试智能拍照 (smart_capture) ---")
    saved_path = capturer.smart_capture(
        quality=15,
        retry_analysis_limit=6,
        retry_capture_limit=5,
        brightness_threshold=2.5
    )
    if saved_path:
        print("✅ 智能拍照成功:", saved_path)
    else:
        print("❌ 智能拍照失败")

    capturer.cleanup()
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))