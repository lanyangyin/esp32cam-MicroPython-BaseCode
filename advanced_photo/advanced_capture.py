# advanced_photo/advanced_capture.py
"""
高级拍照模块

提供单张高级拍照功能，支持：
    - 闪光灯模式：开启、关闭、自动（完整亮度分析）、自动（快速估计）
    - 可配置的分辨率、白平衡、翻转、镜像、图像参数（包括时钟、饱和度、亮度、对比度）
    - 黑照检测与重试
    - 亮度分析重试
    - 可选择保存到 SD 卡或仅返回 JPEG 数据

依赖 photo 包中的 gray_analyzer_capture、gray_quick_capture，
以及 camera_driver.capture_image 和 decision.black_photo.is_black_photo。
"""

import time
import camera
from photo import gray_analyzer_capture, gray_quick_capture
from decision.black_photo import is_black_photo
from flash import get_flash
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR
from camera_driver import capture_image  # 直接使用底层函数，支持所有参数


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
    brightness_threshold=30,
    flash_pin=4,
    flash_on_value=1,
):
    """
    高级拍照函数，支持自动闪光灯决策和黑照重试。

    参数：
        flash_mode (str): 闪光灯模式，可选：
            - 'on'   : 强制开启闪光灯，不进行亮度分析
            - 'off'  : 强制关闭闪光灯，不进行亮度分析
            - 'auto' : 自动模式，使用完整亮度分析（gray_analyzer_capture）
                       决定是否开启闪光灯
            - 'auto_quick' : 快速自动模式，使用 9 点快速亮度估计
                             （gray_quick_capture）决定是否开启闪光灯
        resolution (int): 拍照分辨率常量，如 camera.FRAME_XGA。
        whitebalance (int): 白平衡模式，如 camera.WB_CLOUDY。
        mirror (int): 左右镜像，0 关闭，1 开启。
        flip (int): 上下翻转，0 关闭，1 开启。
        xclk_freq (int): 摄像头主时钟频率，如 camera.XCLK_10MHz。
        saturation (int): 饱和度，-2 ~ 2。
        brightness (int): 亮度，-2 ~ 2。注意：此参数与内部使用的平均亮度变量同名，但作用域不同。
        contrast (int): 对比度，-2 ~ 2。
        quality (int): JPEG 质量，10 ~ 63，数值越小画质越高。
        save_file (bool): 是否保存到 SD 卡。True 返回文件路径，False 返回 JPEG 数据。
        filename_prefix (str): 保存的文件名前缀（不含扩展名），
                               最终文件名格式为 "{prefix}_{timestamp}.jpg"。
        save_path (str): 保存目录，默认为 '/sd'。
        black_retry (int): 黑照检测后的最大重试次数（不包括首次尝试）。
        analysis_retry (int): 亮度分析（auto 或 auto_quick 模式）的最大重试次数。
        analysis_resolution (int): 亮度分析时使用的分辨率，通常低于拍照分辨率以加快速度。
        brightness_threshold (float): 亮度阈值，当平均亮度低于此值时认为场景偏暗，
                                     在 auto/auto_quick 模式下决定是否开启闪光灯。
        flash_pin (int): 闪光灯 GPIO 引脚号。
        flash_on_value (int): 点亮闪光灯的电平值（1 或 0）。

    返回：
        str or bytes or None:
            - 如果 save_file=True 且成功保存，返回文件路径（str）。
            - 如果 save_file=False 且捕获成功，返回 JPEG 数据（bytes）。
            - 如果失败，返回 None。

    注意：
        - 在 auto/auto_quick 模式下，会先进行亮度分析（可能重试），
          然后根据亮度阈值决定是否开启闪光灯。
        - 拍照后会对 JPEG 数据进行黑照检测，若检测为黑照且未达重试上限，
          则重新拍照（重复上述流程）。
        - 所有摄像头操作完成后自动释放资源。
    """
    debug_log("高级拍照启动: flash_mode={}, resolution={}".format(flash_mode, resolution),
              level=LEVEL_INFO, module="AdvancedPhoto")

    # 1. 根据 flash_mode 决定是否需要进行亮度分析
    need_analysis = flash_mode in ('auto', 'auto_quick')
    use_flash = False

    if need_analysis:
        avg_brightness_val = None
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
                    break
            # 分析失败，等待后重试
            time.sleep_ms(100)

        if avg_brightness_val is None:
            debug_log("亮度分析失败，使用保守默认值（偏暗）", level=LEVEL_WARNING, module="AdvancedPhoto")
            avg_brightness_val = 0

        use_flash = avg_brightness_val < brightness_threshold
        debug_log("平均亮度: {:.1f}, 阈值: {}, 决策: {}".format(
            avg_brightness_val, brightness_threshold, "开启" if use_flash else "关闭"),
            level=LEVEL_INFO, module="AdvancedPhoto")
    else:
        use_flash = (flash_mode == 'on')
        debug_log("手动模式: 闪光灯 {}".format("开启" if use_flash else "关闭"),
                  level=LEVEL_INFO, module="AdvancedPhoto")

    # 2. 拍照循环（含黑照重试）
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    final_result = None

    for attempt in range(black_retry + 1):  # 首次尝试 + 重试次数
        debug_log("拍照尝试 {}/{}".format(attempt + 1, black_retry + 1),
                  level=LEVEL_INFO, module="AdvancedPhoto")

        # 控制闪光灯
        if use_flash:
            flash.on()
            time.sleep_ms(200)  # 预闪延时
        else:
            flash.off()

        # 直接调用 capture_image，传递所有参数
        jpeg_data = capture_image(
            framesize=resolution,
            quality=quality,
            format=camera.JPEG,
            fb_location=camera.PSRAM,
            xclk_freq=xclk_freq,
            flip=flip,
            mirror=mirror,
            saturation=saturation,
            brightness=brightness,      # 这里的 brightness 是参数，用于摄像头调节
            contrast=contrast,
            whitebalance=whitebalance,
            effect=camera.EFFECT_NONE
        )

        flash.off()

        if jpeg_data is None:
            debug_log("捕获失败", level=LEVEL_WARNING, module="AdvancedPhoto")
            continue

        # 黑照检测（使用刚捕获的数据）
        if is_black_photo(jpeg_data, resolution):
            debug_log("检测到黑照，重试", level=LEVEL_WARNING, module="AdvancedPhoto")
            continue

        # 处理结果
        if save_file:
            timestamp = int(time.time())
            filename = "{}/{}_{}.jpg".format(save_path.rstrip('/'), filename_prefix, timestamp)
            try:
                with open(filename, 'wb') as f:
                    f.write(jpeg_data)
                final_result = filename
                debug_log("照片已保存: {}".format(filename), level=LEVEL_INFO, module="AdvancedPhoto")
                break
            except Exception as e:
                debug_log("保存失败: {}".format(e), level=LEVEL_ERROR, module="AdvancedPhoto")
                continue
        else:
            final_result = jpeg_data
            break

    if final_result is None:
        debug_log("拍照失败（超过重试次数）", level=LEVEL_ERROR, module="AdvancedPhoto")
        return None

    debug_log("高级拍照完成，结果: {}".format(final_result), level=LEVEL_INFO, module="AdvancedPhoto")
    return final_result


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("=== 高级拍照模块测试 ===")
    # 测试各种模式，并故意设置一些图像参数
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
            brightness_threshold=30,
            # 额外参数验证
            xclk_freq=camera.XCLK_10MHz,
            saturation=1,
            brightness=1,
            contrast=1,
        )
        if result:
            print("✅ 成功: {}".format(result))
        else:
            print("❌ 失败")