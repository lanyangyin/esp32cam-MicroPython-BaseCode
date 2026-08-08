# photo/photo_taker.py
"""
智能拍照流程：先分析亮度，决定是否开闪光灯，再拍照并校验是否黑照。
"""
import time
import gc
import camera
from camera_driver import capture_grayscale, capture_image, get_camera, reset_camera
from utils.brightness import quick_brightness_estimate, analyze_brightness
from decision.retry import should_retry, get_retry_reason
from decision.flash import should_use_flash
from decision.black_photo import is_black_photo
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR
from flash import get_flash
from sd_card import get_sd_card
from utils import get_image_dimensions
from camera_driver import CameraController


def smart_capture_with_analysis(
    analysis_framesize=camera.FRAME_QVGA,
    photo_framesize=camera.FRAME_XGA,
    flash_pin=4,
    flash_on_value=1,
    retry_analysis_limit=6,
    retry_capture_limit=6,
    quality=10,
    sd_mount_point="/sd"
):
    """
    完整的智能拍照流程：
    1. 分析阶段：最多 retry_analysis_limit 次捕获灰度图，快速估计亮度，若亮度信息异常则重试。
    2. 闪光灯决策：根据最终亮度决定是否开闪光灯。
    3. 拍照阶段：最多 retry_capture_limit 次捕获 JPEG，每次检查是否为黑照，如果是则重试；否则保存并返回路径。

    参数：
        analysis_framesize (int): 用于亮度分析的分辨率（默认 QVGA，速度快）。
        photo_framesize (int): 最终照片的分辨率。
        flash_pin (int): 闪光灯 GPIO 引脚。
        flash_on_value (int): 闪光灯点亮电平。
        retry_analysis_limit (int): 分析阶段最大重试次数。
        retry_capture_limit (int): 拍照阶段最大重试次数。
        quality (int): JPEG 质量（10~63）。
        sd_mount_point (str): SD 卡挂载点。

    返回：
        tuple: (saved_path, actual_width, actual_height, brightness_info)
               若失败，saved_path 为 None。
    """
    debug_log("智能拍照流程启动", level=LEVEL_INFO, module="PhotoTaker")

    # ---------- 1. 分析阶段 ----------
    final_brightness = None
    for attempt in range(1, retry_analysis_limit + 1):
        debug_log("分析阶段 尝试 {}/{}".format(attempt, retry_analysis_limit), level=LEVEL_INFO, module="PhotoTaker")
        reset_camera()
        gc.collect()
        time.sleep_ms(200)

        gray_buf = capture_grayscale(framesize=analysis_framesize, whitebalance=camera.WB_CLOUDY)
        if gray_buf is None:
            debug_log("灰度捕获失败", level=LEVEL_WARNING, module="PhotoTaker")
            continue

        w, h = CameraController.get_resolution(analysis_framesize)
        if w is None or h is None:
            total = len(gray_buf)
            w = int((total * 4 / 3) ** 0.5)
            h = total // w
            if w * h != total:
                w, h = 320, 240

        # 完整分析以获取 avg, dynamic, center
        brightness_info = analyze_brightness(gray_buf, w, h, step=2)
        if brightness_info is None:
            debug_log("亮度分析失败", level=LEVEL_WARNING, module="PhotoTaker")
            continue

        # 新增：详细输出亮度信息
        debug_log("亮度信息: avg={:.1f}, dynamic={}, center={:.1f}".format(
            brightness_info['average_brightness'],
            brightness_info['dynamic_range'],
            brightness_info['center_brightness']
        ), level=LEVEL_INFO, module="PhotoTaker")

        if should_retry(brightness_info):
            # 新增：输出重试原因（从 retry_decision 获取）
            retry_reason = get_retry_reason(brightness_info)  # 需要导入
            debug_log("亮度信息异常，需要重试分析: {}".format(retry_reason), level=LEVEL_WARNING,
                      module="PhotoTaker")
            if attempt == retry_analysis_limit:
                final_brightness = brightness_info
                debug_log("达到最大分析重试次数，使用最后一次亮度信息", level=LEVEL_WARNING, module="PhotoTaker")
                break
            else:
                continue
        else:
            final_brightness = brightness_info
            debug_log("亮度信息正常，分析完成", level=LEVEL_INFO, module="PhotoTaker")
            break

    if final_brightness is None:
        debug_log("分析阶段全部失败，使用保守默认亮度（avg=0）", level=LEVEL_ERROR, module="PhotoTaker")
        final_brightness = {"average_brightness": 0, "dynamic_range": 0, "center_brightness": 0}

    # ---------- 2. 闪光灯决策 ----------
    need_flash = should_use_flash(final_brightness)
    debug_log("闪光灯决策: {}".format("需要" if need_flash else "不需要"), level=LEVEL_INFO, module="PhotoTaker")

    # ---------- 3. 拍照阶段 ----------
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    sd = get_sd_card(mount_point=sd_mount_point)

    photo_w, photo_h = CameraController.get_resolution(photo_framesize)
    if photo_w is None or photo_h is None:
        photo_w, photo_h = 0, 0

    for attempt in range(1, retry_capture_limit + 1):
        debug_log("拍照阶段 尝试 {}/{}".format(attempt, retry_capture_limit), level=LEVEL_INFO, module="PhotoTaker")

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

        if jpeg_data is None:
            debug_log("JPEG 捕获失败", level=LEVEL_WARNING, module="PhotoTaker")
            continue

        if is_black_photo(jpeg_data, photo_framesize):
            debug_log("检测到黑照（尺寸过小），重试", level=LEVEL_WARNING, module="PhotoTaker")
            continue

        # 照片有效，保存
        debug_log("照片大小正常，保存", level=LEVEL_INFO, module="PhotoTaker")

        # 照片有效，保存
        filename = "/sd/photo_{}.jpg".format(int(time.time()))
        saved_path = sd.save_file(jpeg_data, filename)
        if saved_path:
            w_actual, h_actual = get_image_dimensions(jpeg_data)
            if w_actual == 0 or h_actual == 0:
                w_actual, h_actual = photo_w, photo_h
            debug_log("✅ 照片保存成功: {} ({}×{}, {} bytes)".format(
                saved_path, w_actual, h_actual, len(jpeg_data)), level=LEVEL_INFO, module="PhotoTaker")
            return saved_path, w_actual, h_actual, final_brightness
        else:
            debug_log("照片保存失败", level=LEVEL_ERROR, module="PhotoTaker")
            return None, 0, 0, final_brightness

    debug_log("拍照阶段全部失败，无法保存照片", level=LEVEL_ERROR, module="PhotoTaker")
    return None, 0, 0, final_brightness



if __name__ == "__main__":
    saved_path, w, h, brightness = smart_capture_with_analysis(
        analysis_framesize=camera.FRAME_QVGA,
        photo_framesize=camera.FRAME_XGA,
        retry_analysis_limit=6,
        retry_capture_limit=6
    )
    if saved_path:
        print("照片保存成功: {}, 尺寸: {}x{}, 亮度: {:.1f}".format(
            saved_path, w, h, brightness['average_brightness']))
    else:
        print("拍照失败")