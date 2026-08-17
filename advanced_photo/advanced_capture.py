# advanced_photo/advanced_capture.py
"""
高级拍照模块（优化版，将摄像头初始化移到循环外）
"""

import time
import camera
from photo import gray_analyzer_capture, gray_quick_capture
from decision.black_photo import is_black_photo
from decision.flash import should_use_flash
from decision.quick_flash import quick_should_use_flash
from flash import get_flash
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR
from camera_driver import capture_image, get_camera
from utils import get_image_dimensions


def take_advanced_photo(
    flash_mode='auto',
    resolution=camera.FRAME_XGA,
    whitebalance=camera.WB_CLOUDY,
    mirror=0,
    flip=1,
    xclk_freq=camera.XCLK_10MHz,
    saturation=0,
    brightness=0,
    contrast=0,
    quality=10,
    save_file=True,
    filename_prefix='photo',
    save_path='/sd',
    black_retry=3,
    analysis_retry=3,
    analysis_resolution=camera.FRAME_QVGA,
    flash_pin=4,
    flash_on_value=1,
    flash_brightness=100,
):
    """
    高级拍照函数，支持自动闪光灯决策和黑照重试。
    """
    debug_log("高级拍照启动: flash_mode={}, resolution={}".format(flash_mode, resolution),
              level=LEVEL_INFO, module="AdvancedPhoto")

    # 1. 闪光灯决策
    need_analysis = flash_mode in ('auto', 'auto_quick')
    use_flash = False
    avg_brightness_val = None

    if need_analysis:
        for attempt in range(1, analysis_retry + 1):
            debug_log("亮度分析尝试 {}/{}".format(attempt, analysis_retry),
                      level=LEVEL_INFO, module="AdvancedPhoto")
            if flash_mode == 'auto':
                info = gray_analyzer_capture(
                    framesize=analysis_resolution,
                    whitebalance=whitebalance,
                    flip=flip,
                    mirror=mirror
                )
                if info is not None:
                    avg_brightness_val = info.get('average_brightness')
                    use_flash = should_use_flash(info)
                    debug_log("规则引擎决策: flash={}".format(use_flash),
                              level=LEVEL_INFO, module="AdvancedPhoto")
                    break
            else:  # auto_quick
                avg = gray_quick_capture(
                    framesize=analysis_resolution,
                    whitebalance=whitebalance,
                    flip=flip,
                    mirror=mirror
                )
                if avg is not None:
                    avg_brightness_val = avg
                    use_flash = quick_should_use_flash(avg)
                    debug_log("快速阈值决策: flash={}".format(use_flash),
                              level=LEVEL_INFO, module="AdvancedPhoto")
                    break
            time.sleep_ms(100)

        if avg_brightness_val is None:
            debug_log("亮度分析失败，使用保守默认（关闭闪光灯）",
                      level=LEVEL_WARNING, module="AdvancedPhoto")
            avg_brightness_val = 0
            use_flash = False

        debug_log("最终平均亮度: {:.1f}, 决策: {}".format(
            avg_brightness_val, "开启" if use_flash else "关闭"),
            level=LEVEL_INFO, module="AdvancedPhoto")
    else:
        use_flash = (flash_mode == 'on')
        debug_log("手动模式: 闪光灯 {}".format("开启" if use_flash else "关闭"),
                  level=LEVEL_INFO, module="AdvancedPhoto")

    # 2. 摄像头初始化（移到循环外，只初始化一次）
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    # 初始化摄像头（获取实例并配置参数）
    cam = get_camera(
        framesize=resolution,
        quality=quality,
        format=camera.JPEG,
        fb_location=camera.PSRAM,
        xclk_freq=xclk_freq,
        flip=flip,
        mirror=mirror,
        saturation=saturation,
        brightness=brightness,
        contrast=contrast,
        whitebalance=whitebalance,
        effect=camera.EFFECT_NONE
    )
    if cam is None or not cam.initialized:
        debug_log("摄像头初始化失败", level=LEVEL_ERROR, module="AdvancedPhoto")
        return None

    final_jpeg = None
    final_path = None

    for attempt in range(black_retry + 1):
        debug_log("拍照尝试 {}/{}".format(attempt + 1, black_retry + 1),
                  level=LEVEL_INFO, module="AdvancedPhoto")

        if use_flash:
            flash.set_brightness(flash_brightness)
            time.sleep_ms(200)
        else:
            flash.off()

        # 直接使用 cam.capture() 捕获（不重新初始化）
        for _ in range(brightness + 2):
            cam.capture()
        jpeg_data = cam.capture()

        flash.off()

        if jpeg_data is None:
            debug_log("捕获失败", level=LEVEL_WARNING, module="AdvancedPhoto")
            continue

        if is_black_photo(jpeg_data, resolution):
            debug_log("检测到黑照，重试", level=LEVEL_WARNING, module="AdvancedPhoto")
            continue

        final_jpeg = jpeg_data
        break

    # 释放摄像头
    cam.deinit()

    if final_jpeg is None:
        debug_log("拍照失败（超过重试次数）", level=LEVEL_ERROR, module="AdvancedPhoto")
        return None

    # 解析尺寸
    width, height = get_image_dimensions(final_jpeg)
    if width == 0 or height == 0:
        from camera_driver import CameraController
        w, h = CameraController.get_resolution(resolution)
        width, height = w or 0, h or 0

    # 保存
    if save_file:
        timestamp = int(time.time())
        filename = "{}/{}_{}.jpg".format(save_path.rstrip('/'), filename_prefix, timestamp)
        try:
            with open(filename, 'wb') as f:
                f.write(final_jpeg)
            final_path = filename
            debug_log("照片已保存: {}".format(filename), level=LEVEL_INFO, module="AdvancedPhoto")
        except Exception as e:
            debug_log("保存失败: {}".format(e), level=LEVEL_ERROR, module="AdvancedPhoto")
            return None
    else:
        final_path = None

    result = {
        'path': final_path,
        'data': final_jpeg if not save_file else None,
        'brightness': avg_brightness_val,
        'width': width,
        'height': height,
    }
    return result