# advanced_photo/burst_capture.py
"""
连拍模块

提供连续拍摄多张照片的功能，可控制闪光灯，并记录总耗时。
所有照片保存到 SD 卡，文件名自动添加序号。
"""

import time
import camera
from camera_driver import get_camera, reset_camera
from flash import get_flash
from sd_card import get_sd_card
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR


def burst_capture(
    resolution=camera.FRAME_XGA,
    whitebalance=camera.WB_CLOUDY,
    mirror=0,
    flip=1,
    burst_count=5,
    xclk_freq=camera.XCLK_10MHz,
    saturation=0,
    brightness=0,
    contrast=0,
    quality=10,
    flash_on=False,
    filename_prefix='burst',
    save_path='/sd',
    flash_pin=4,
    flash_on_value=1,
    pre_flash_delay=200,
):
    """
    连拍多张照片，并返回总耗时。

    参数：
        resolution (int): 拍照分辨率常量。
        whitebalance (int): 白平衡模式。
        mirror (int): 左右镜像，0 关闭，1 开启。
        flip (int): 上下翻转，0 关闭，1 开启。
        burst_count (int): 连拍张数。
        xclk_freq (int): 摄像头主时钟频率。
        saturation (int): 饱和度，-2 ~ 2。
        brightness (int): 亮度，-2 ~ 2。
        contrast (int): 对比度，-2 ~ 2。
        quality (int): JPEG 质量，10 ~ 63。
        flash_on (bool): 是否开启闪光灯（整个连拍过程中保持开启）。
        filename_prefix (str): 文件名前缀，最终格式为 "{prefix}_{序号}.jpg"，
                              序号从 1 开始递增。
        save_path (str): 保存目录，默认为 '/sd'。
        flash_pin (int): 闪光灯 GPIO 引脚号。
        flash_on_value (int): 点亮闪光灯的电平值。
        pre_flash_delay (int): 闪光灯开启后到拍摄的延时（毫秒）。

    返回：
        float: 连拍总耗时（秒）。若发生严重错误，返回 -1.0。
    """
    debug_log("连拍启动: 张数={}, 分辨率={}".format(burst_count, resolution),
              level=LEVEL_INFO, module="BurstCapture")

    if burst_count <= 0:
        debug_log("连拍张数必须大于0", level=LEVEL_ERROR, module="BurstCapture")
        return -1.0

    # 初始化摄像头（一次性，整个连拍过程保持初始化）
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
        debug_log("摄像头初始化失败", level=LEVEL_ERROR, module="BurstCapture")
        return -1.0

    # 挂载 SD 卡
    sd = get_sd_card(mount_point=save_path)
    if not sd.mounted:
        debug_log("SD 卡未挂载", level=LEVEL_ERROR, module="BurstCapture")
        cam.deinit()
        return -1.0

    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    if flash_on:
        flash.on()
        time.sleep_ms(pre_flash_delay)  # 预闪

    start_time = time.time()
    success_count = 0
    try:
        for i in range(1, burst_count + 1):
            debug_log("拍摄第 {} 张".format(i), level=LEVEL_INFO, module="BurstCapture")
            # 捕获
            try:
                for _ in range(3):
                    cam.capture()
                jpeg_data = cam.capture()
            except Exception as e:
                debug_log("第 {} 张捕获异常: {}".format(i, e), level=LEVEL_WARNING, module="BurstCapture")
                continue

            if jpeg_data is None:
                debug_log("第 {} 张捕获失败（无数据）".format(i), level=LEVEL_WARNING, module="BurstCapture")
                continue

            # 构造文件名
            filename = "{}/{}_{:03d}.jpg".format(save_path.rstrip('/'), filename_prefix, i)
            try:
                with open(filename, 'wb') as f:
                    f.write(jpeg_data)
                success_count += 1
                debug_log("第 {} 张已保存: {}".format(i, filename), level=LEVEL_INFO, module="BurstCapture")
            except Exception as e:
                debug_log("第 {} 张保存失败: {}".format(i, e), level=LEVEL_WARNING, module="BurstCapture")
    finally:
        # 关闭闪光灯并释放摄像头
        flash.off()
        cam.deinit()

    elapsed = time.time() - start_time
    debug_log("连拍完成: 成功 {} / {}, 耗时 {:.2f} 秒".format(
        success_count, burst_count, elapsed), level=LEVEL_INFO, module="BurstCapture")

    if success_count == 0:
        debug_log("连拍全部失败", level=LEVEL_ERROR, module="BurstCapture")
        return -1.0

    return elapsed


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("=== 连拍模块测试 ===")
    elapsed = burst_capture(
        resolution=camera.FRAME_HD,
        burst_count=6,
        flash_on=False,
        filename_prefix="test_burst",
        save_path="/sd"
    )
    if elapsed > 0:
        print("✅ 连拍完成，耗时: {:.2f} 秒".format(elapsed))
    else:
        print("❌ 连拍失败")