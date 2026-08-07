# photo/smart_flow.py
"""智能拍照流程（原 PhotoCapturer.smart_capture 的主体）"""
import math
import time
import camera  # type: ignore
from camera_driver import get_camera, CameraController, capture_grayscale, capture_image
from flash import get_flash
from sd_card import get_sd_card
from decision import should_use_flash, should_retry
from utils.brightness import analyze_brightness, quick_brightness_estimate
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[SmartFlow] " + msg)

def smart_capture_flow(capturer, filename=None, quality=10,
                       pre_flash_delay=200, retry_analysis_limit=6,
                       retry_capture_limit=5, brightness_threshold=2.5,
                       auto_deinit=True):
    """执行智能拍照流程"""
    _debug_log("smart_capture called, filename={}".format(filename))
    print("\n[智能拍照] 启动...")

    flash = get_flash(pin=capturer.flash_pin, on_value=capturer.flash_on_value)
    sd = get_sd_card(mount_point=capturer.sd_mount_point)
    framesize = capturer.camera_params.get("framesize", camera.FRAME_XGA)

    # ---- 预分析阶段 ----
    _debug_log("=== 预分析阶段（最多 {} 次）===".format(retry_analysis_limit))
    final_brightness = None

    for attempt in range(1, retry_analysis_limit + 1):
        _debug_log("预分析尝试 {}/{}".format(attempt, retry_analysis_limit))
        print("  预分析 {}/{}...".format(attempt, retry_analysis_limit))
        flash.off()

        gray_buf = capture_grayscale(
            framesize=framesize,
            whitebalance=camera.WB_CLOUDY
        )
        if gray_buf is None:
            _debug_log("灰度捕获失败，重试")
            continue

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            total = len(gray_buf)
            w = int(math.sqrt(total * 4 / 3))
            h = total // w
            if w * h != total:
                w, h = 640, 480

        brightness_info = analyze_brightness(gray_buf, w, h, step=2)
        if brightness_info is None:
            _debug_log("亮度分析失败，重试")
            continue

        _debug_log("亮度信息: avg={:.1f}, dynamic={}, center={:.1f}".format(
            brightness_info['average_brightness'],
            brightness_info['dynamic_range'],
            brightness_info['center_brightness']
        ))

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

    if final_brightness is None:
        _debug_log("预分析全部失败，使用保守默认亮度（avg=0）")
        final_brightness = {"average_brightness": 0, "dynamic_range": 0, "center_brightness": 0}

    # ---- 闪光灯决策 ----
    need_flash = should_use_flash(final_brightness)
    _debug_log("闪光灯决策: {}".format("需要" if need_flash else "不需要"))
    print("  闪光灯: {}".format("✅ 开启" if need_flash else "❌ 关闭"))

    # ---- 拍照阶段 ----
    _debug_log("=== 拍照阶段（最多 {} 次）===".format(retry_capture_limit))
    jpeg_data = None
    final_path = None

    for attempt in range(1, retry_capture_limit + 1):
        _debug_log("拍照尝试 {}/{}".format(attempt, retry_capture_limit))
        print("  拍照 {}/{}...".format(attempt, retry_capture_limit))

        if need_flash:
            flash.on()
            time.sleep_ms(pre_flash_delay)
            _debug_log("闪光灯已开启")
        else:
            flash.off()
            _debug_log("闪光灯已关闭")

        gray_buf = capture_grayscale(
            framesize=framesize,
            whitebalance=camera.WB_CLOUDY
        )
        if gray_buf is None:
            _debug_log("灰度捕获失败，重试")
            continue

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            total = len(gray_buf)
            w = int(math.sqrt(total * 4 / 3))
            h = total // w
            if w * h != total:
                w, h = 640, 480

        est_avg = quick_brightness_estimate(gray_buf, w, h)
        if est_avg is None:
            _debug_log("快速估计失败，重试")
            continue

        _debug_log("快速估计亮度: {:.1f}".format(est_avg))
        print("    亮度估计: {:.1f} (阈值 {:.1f})".format(est_avg, brightness_threshold))

        if est_avg > brightness_threshold:
            _debug_log("亮度合格，拍摄 JPEG")
            print("    ✅ 亮度合格，正在保存照片...")

            if need_flash:
                flash.on()
                time.sleep_ms(pre_flash_delay)
            else:
                flash.off()

            jpeg_data = capture_image(
                framesize=framesize,
                quality=quality,
                format=camera.JPEG,
                flip=capturer.camera_params.get("flip", 1),
                mirror=capturer.camera_params.get("mirror", 0),
                whitebalance=camera.WB_CLOUDY
            )
            flash.off()

            if jpeg_data is None:
                _debug_log("JPEG 捕获失败，重试")
                continue

            if filename is None:
                filename = "smart_photo_{}.jpg".format(time.time())
            if not filename.startswith(capturer.sd_mount_point):
                filename = capturer.sd_mount_point + "/" + filename.lstrip("/")

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

    # ---- 强制兜底保存 ----
    if final_path is None:
        _debug_log("拍照阶段结束，未保存任何照片，尝试最后一次保存")
        print("  ⚠️ 所有尝试均未合格，保存最后一次 JPEG...")

        if need_flash:
            flash.on()
            time.sleep_ms(pre_flash_delay)
        else:
            flash.off()

        jpeg_data = capture_image(
            framesize=framesize,
            quality=quality,
            format=camera.JPEG,
            flip=capturer.camera_params.get("flip", 1),
            mirror=capturer.camera_params.get("mirror", 0),
            whitebalance=camera.WB_CLOUDY
        )
        flash.off()

        if jpeg_data is not None:
            if filename is None:
                filename = "smart_photo_fallback_{}.jpg".format(time.time())
            if not filename.startswith(capturer.sd_mount_point):
                filename = capturer.sd_mount_point + "/" + filename.lstrip("/")
            try:
                with open(filename, "wb") as f:
                    f.write(jpeg_data)
                final_path = filename
                _debug_log("备用照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
                print("  ✅ 备用照片已保存: {} ({} bytes)".format(filename, len(jpeg_data)))
            except Exception as e:
                _debug_log("备用保存失败: {}".format(e))
                print("  ❌ 备用保存失败: {}".format(e))

    if auto_deinit:
        cam = get_camera()
        if cam.initialized:
            cam.deinit()
            _debug_log("摄像头已释放")

    print("[智能拍照] 完成")
    return final_path