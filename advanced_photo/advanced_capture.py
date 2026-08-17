# advanced_photo/advanced_capture.py
"""
高级拍照模块

提供单张高级拍照功能，支持：
    - 闪光灯模式：开启、关闭、自动（完整亮度分析）、自动（快速估计）
    - 可配置的分辨率、白平衡、翻转、镜像、图像参数
    - 黑照检测与重试
    - 亮度分析重试
    - 可选择保存到 SD 卡或仅返回 JPEG 数据
    - 闪光灯亮度控制（0~100）

依赖 photo 包中的 gray_analyzer_capture、gray_quick_capture，
camera_driver.capture_image，decision.flash.should_use_flash，
decision.quick_flash.quick_should_use_flash 和 decision.black_photo.is_black_photo。
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
    高级拍照函数，支持自动闪光灯决策（基于配置文件）和黑照重试。

    参数：
        flash_mode (str): 闪光灯模式，可选：
            - 'on'   : 强制开启闪光灯，不进行亮度分析
            - 'off'  : 强制关闭闪光灯，不进行亮度分析
            - 'auto' : 自动模式，使用完整亮度分析（gray_analyzer_capture）
                       并依据 flash_guide.json 规则引擎决定是否开启闪光灯
            - 'auto_quick' : 快速自动模式，使用 9 点快速亮度估计
                             （gray_quick_capture）并依据 quick_flash_guide.json
                             阈值配置决定是否开启闪光灯
        resolution (int): 拍照分辨率常量，如 camera.FRAME_XGA。
        whitebalance (int): 白平衡模式，如 camera.WB_CLOUDY。
        mirror (int): 左右镜像，0 关闭，1 开启。
        flip (int): 上下翻转，0 关闭，1 开启。
        xclk_freq (int): 摄像头主时钟频率，如 camera.XCLK_10MHz。
        saturation (int): 饱和度，-2 ~ 2。
        brightness (int): 亮度，-2 ~ 2。
        contrast (int): 对比度，-2 ~ 2。
        quality (int): JPEG 质量，10 ~ 63，数值越小画质越高。
        save_file (bool): 是否保存到 SD 卡。True 返回文件路径，False 返回 JPEG 数据。
        filename_prefix (str): 保存的文件名前缀（不含扩展名），
                               最终文件名格式为 "{prefix}_{timestamp}.jpg"。
        save_path (str): 保存目录，默认为 '/sd'。
        black_retry (int): 黑照检测后的最大重试次数（不包括首次尝试）。
        analysis_retry (int): 亮度分析（auto 或 auto_quick 模式）的最大重试次数。
        analysis_resolution (int): 亮度分析时使用的分辨率，通常低于拍照分辨率以加快速度。
        flash_pin (int): 闪光灯 GPIO 引脚号。
        flash_on_value (int): 点亮闪光灯的电平值（1 或 0）。
        flash_brightness (int): 闪光灯亮度百分比（0~100），仅在闪光灯开启时有效，默认100。

    返回：
        dict or None: 成功时返回包含以下键的字典：
            - 'path' (str): 保存的文件路径（如果 save_file=True）或 None
            - 'data' (bytes): JPEG 数据（如果 save_file=False）或 None
            - 'brightness' (float): 分析得到的平均亮度（若未分析则为 None）
            - 'width' (int): 图像宽度
            - 'height' (int): 图像高度
            失败时返回 None。
    """
    debug_log("高级拍照启动: flash_mode={}, resolution={}".format(flash_mode, resolution),
              level=LEVEL_INFO, module="AdvancedPhoto")

    # 1. 根据 flash_mode 决定是否需要进行亮度分析
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

    # 2. 拍照循环（含黑照重试）
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    final_jpeg = None
    final_path = None

    for attempt in range(black_retry + 1):
        debug_log("拍照尝试 {}/{}".format(attempt + 1, black_retry + 1),
                  level=LEVEL_INFO, module="AdvancedPhoto")

        if use_flash:
            # 直接设置亮度（替代 flash.on()）
            flash.set_brightness(flash_brightness)
            time.sleep_ms(200)
        else:
            flash.off()

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
        for _ in range(brightness+2):
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

    if final_jpeg is None:
        debug_log("拍照失败（超过重试次数）", level=LEVEL_ERROR, module="AdvancedPhoto")
        return None

    # 解析图像尺寸
    width, height = get_image_dimensions(final_jpeg)
    if width == 0 or height == 0:
        from camera_driver import CameraController
        w, h = CameraController.get_resolution(resolution)
        width, height = w or 0, h or 0

    # 保存或返回数据
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


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("=== 高级拍照模块测试 ===")
    for mode in ('on', 'off', 'auto', 'auto_quick'):
        print("\n测试闪光灯模式: {}".format(mode))
        result = take_advanced_photo(
            flash_mode=mode,
            resolution=camera.FRAME_VGA,
            save_file=True,
            filename_prefix="test_{}".format(mode),
            save_path="/sd",
            black_retry=1,
            analysis_retry=1,
            analysis_resolution=camera.FRAME_QVGA,
            flash_brightness=50,  # 测试亮度
        )
        if result:
            print("✅ 成功: 路径={}, 亮度={:.1f}, 尺寸={}x{}".format(
                result['path'], result['brightness'], result['width'], result['height']))
        else:
            print("❌ 失败")