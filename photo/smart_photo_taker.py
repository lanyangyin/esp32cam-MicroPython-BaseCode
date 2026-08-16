# photo/smart_photo_taker.py (修改后的完整代码)
"""
智能拍照流程：先分析亮度，决定是否开闪光灯，再拍照并校验是否黑照。
支持正常闪光灯决策（规则引擎）和快速闪光灯决策（阈值）。
"""
import time
import gc
import camera
from camera_driver import capture_grayscale, capture_image, get_camera, reset_camera
from utils.brightness import quick_brightness_estimate, analyze_brightness
from decision.retry import should_retry, get_retry_reason
from decision.flash import should_use_flash
from decision.quick_flash import quick_should_use_flash
from decision.black_photo import is_black_photo
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR
from flash import get_flash
from sd_card import get_sd_card
from utils import get_image_dimensions
from camera_driver import CameraController
from indicator import get_indicator


def take_smart_photo(
    analysis_framesize=camera.FRAME_QVGA,
    photo_framesize=camera.FRAME_XGA,
    flash_pin=4,
    flash_on_value=1,
    retry_analysis_limit=6,
    retry_capture_limit=6,
    quality=10,
    sd_mount_point="/sd",
    decision_mode='normal'  # 'normal' 或 'quick'
):
    """
    完整的智能拍照流程（自动决定闪光灯）。

    Args:
        decision_mode (str): 闪光灯决策模式。
            - 'normal': 使用完整的规则引擎（flash_guide.json），包含重拍逻辑
            - 'quick': 使用快速阈值决策（quick_flash_guide.json），无重拍，仅快速亮度估计
    """
    if decision_mode not in ('normal', 'quick'):
        raise ValueError("decision_mode 必须是 'normal' 或 'quick'")

    debug_log("智能拍照流程启动", level=LEVEL_INFO, module="SmartPhotoTaker")
    debug_log("决策模式: {}".format(decision_mode), level=LEVEL_INFO, module="SmartPhotoTaker")

    # ---------- 1. 分析阶段 ----------
    final_brightness = None

    if decision_mode == 'quick':
        # 快速模式：仅使用快速亮度估计，不重试
        debug_log("快速模式：使用快速亮度估计", level=LEVEL_INFO, module="SmartPhotoTaker")
        # reset_camera()
        gc.collect()
        time.sleep_ms(200)

        indicator = get_indicator()
        indicator.on()
        gray_buf = capture_grayscale(framesize=analysis_framesize, whitebalance=camera.WB_CLOUDY)
        indicator.off()
        if gray_buf is None:
            debug_log("快速亮度估计失败（灰度捕获失败）", level=LEVEL_ERROR, module="SmartPhotoTaker")
            return None, 0, 0, None

        w, h = CameraController.get_resolution(analysis_framesize)
        if w is None or h is None:
            total = len(gray_buf)
            w = int((total * 4 / 3) ** 0.5)
            h = total // w
            if w * h != total:
                w, h = 320, 240

        avg = quick_brightness_estimate(gray_buf, w, h)
        if avg is None:
            debug_log("快速亮度估计失败", level=LEVEL_ERROR, module="SmartPhotoTaker")
            return None, 0, 0, None

        debug_log("快速亮度估计: avg={:.1f}".format(avg), level=LEVEL_INFO, module="SmartPhotoTaker")
        # 构造最小亮度信息用于后续日志
        final_brightness = {"average_brightness": avg}
        need_flash = quick_should_use_flash(avg)

    else:
        # normal 模式：完整的分析和重拍
        debug_log("正常模式：使用完整亮度分析（含重拍）", level=LEVEL_INFO, module="SmartPhotoTaker")
        for attempt in range(1, retry_analysis_limit + 1):
            debug_log("分析阶段 尝试 {}/{}".format(attempt, retry_analysis_limit), level=LEVEL_INFO, module="SmartPhotoTaker")
            reset_camera()
            gc.collect()
            time.sleep_ms(200)

            indicator = get_indicator()
            indicator.on()
            gray_buf = capture_grayscale(framesize=analysis_framesize, whitebalance=camera.WB_CLOUDY)
            indicator.off()
            if gray_buf is None:
                debug_log("灰度捕获失败", level=LEVEL_WARNING, module="SmartPhotoTaker")
                continue

            w, h = CameraController.get_resolution(analysis_framesize)
            if w is None or h is None:
                total = len(gray_buf)
                w = int((total * 4 / 3) ** 0.5)
                h = total // w
                if w * h != total:
                    w, h = 320, 240

            brightness_info = analyze_brightness(gray_buf, w, h, step=2)
            if brightness_info is None:
                debug_log("亮度分析失败", level=LEVEL_WARNING, module="SmartPhotoTaker")
                continue

            debug_log("亮度信息: avg={:.1f}, dynamic={}, center={:.1f}".format(
                brightness_info['average_brightness'],
                brightness_info['dynamic_range'],
                brightness_info['center_brightness']
            ), level=LEVEL_INFO, module="SmartPhotoTaker")

            if should_retry(brightness_info):
                retry_reason = get_retry_reason(brightness_info)
                debug_log("亮度信息异常，需要重试分析: {}".format(retry_reason), level=LEVEL_WARNING,
                          module="SmartPhotoTaker")
                if attempt == retry_analysis_limit:
                    final_brightness = brightness_info
                    debug_log("达到最大分析重试次数，使用最后一次亮度信息", level=LEVEL_WARNING, module="SmartPhotoTaker")
                    break
                else:
                    continue
            else:
                final_brightness = brightness_info
                debug_log("亮度信息正常，分析完成", level=LEVEL_INFO, module="SmartPhotoTaker")
                break

        if final_brightness is None:
            debug_log("分析阶段全部失败，使用保守默认亮度（avg=0）", level=LEVEL_ERROR, module="SmartPhotoTaker")
            final_brightness = {"average_brightness": 0, "dynamic_range": 0, "center_brightness": 0}

        need_flash = should_use_flash(final_brightness)

    debug_log("闪光灯决策: {}".format("需要" if need_flash else "不需要"), level=LEVEL_INFO, module="SmartPhotoTaker")

    # ---------- 拍照阶段（对两种模式相同） ----------
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    sd = get_sd_card(mount_point=sd_mount_point)

    photo_w, photo_h = CameraController.get_resolution(photo_framesize)
    if photo_w is None or photo_h is None:
        photo_w, photo_h = 0, 0

    for attempt in range(1, retry_capture_limit + 1):
        debug_log("拍照阶段 尝试 {}/{}".format(attempt, retry_capture_limit), level=LEVEL_INFO, module="SmartPhotoTaker")

        indicator = get_indicator()
        indicator.on()
        if need_flash:
            flash.on()
            time.sleep_ms(200)
        else:
            flash.off()

        jpeg_data = capture_image(
            framesize=photo_framesize,
            quality=quality,
            format=camera.JPEG,
            flip=1,
            whitebalance=camera.WB_CLOUDY
        )

        flash.off()
        indicator.off()

        if jpeg_data is None:
            debug_log("JPEG 捕获失败", level=LEVEL_WARNING, module="SmartPhotoTaker")
            continue

        if is_black_photo(jpeg_data, photo_framesize):
            debug_log("检测到黑照（尺寸过小），重试", level=LEVEL_WARNING, module="SmartPhotoTaker")
            continue

        # 照片有效，保存
        filename = "/sd/photo_{}.jpg".format(int(time.time()))
        saved_path = sd.save_file(jpeg_data, filename)
        if saved_path:
            w_actual, h_actual = get_image_dimensions(jpeg_data)
            if w_actual == 0 or h_actual == 0:
                w_actual, h_actual = photo_w, photo_h
            debug_log("✅ 照片保存成功: {} ({}×{}, {} bytes)".format(
                saved_path, w_actual, h_actual, len(jpeg_data)), level=LEVEL_INFO, module="SmartPhotoTaker")
            return saved_path, w_actual, h_actual, final_brightness
        else:
            debug_log("照片保存失败", level=LEVEL_ERROR, module="SmartPhotoTaker")
            return None, 0, 0, final_brightness

    debug_log("拍照阶段全部失败，无法保存照片", level=LEVEL_ERROR, module="SmartPhotoTaker")
    return None, 0, 0, final_brightness


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    print("智能拍照测试（需硬件）")
    saved_path, w, h, brightness = take_smart_photo(
        analysis_framesize=camera.FRAME_QVGA,
        photo_framesize=camera.FRAME_XGA,
        retry_analysis_limit=2,
        retry_capture_limit=2,
        decision_mode='quick'  # 测试快速模式
    )
    if saved_path:
        print("照片保存成功: {}, 尺寸: {}x{}, 亮度: {:.1f}".format(
            saved_path, w, h, brightness['average_brightness']))
    else:
        print("拍照失败")