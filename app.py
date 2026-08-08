"""
app.py - ESP32-CAM 简单拍照程序（带自动降级和资源释放）
"""
import time
import gc
import camera
from config import set_debug, debug_log, LEVEL_INFO, LEVEL_ERROR, LEVEL_WARNING
from camera_driver import reset_camera, get_camera, CameraController
from camera_driver.resolutions import get_name_by_value, get_resolution
from flash import get_flash
from sd_card import get_sd_card
from utils import get_image_dimensions

set_debug(True)

# 希望使用的分辨率（将从高到低尝试降级）
PREFERRED_RESOLUTIONS = [
    camera.FRAME_QSXGA,   # 2560x1920
    camera.FRAME_UXGA,    # 1600x1200
    camera.FRAME_XGA,     # 1024x768
    camera.FRAME_SVGA,    # 800x600
    camera.FRAME_VGA,     # 640x480
    camera.FRAME_QVGA,    # 320x240
]

def main():
    debug_log("📷 ESP32-CAM 拍照程序启动", level=LEVEL_INFO, module="app")

    # 1. 尝试初始化摄像头，支持自动降级
    cam = None
    chosen_framesize = None
    set_w = set_h = 0

    for framesize in PREFERRED_RESOLUTIONS:
        res_name = get_name_by_value(framesize) or "UNKNOWN"
        debug_log("尝试初始化分辨率: {} ({})".format(res_name, framesize), level=LEVEL_INFO, module="app")

        # 彻底释放摄像头资源并回收内存
        reset_camera()
        gc.collect()
        time.sleep_ms(300)  # 给硬件足够时间复位

        try:
            cam = get_camera(
                framesize=framesize,
                quality=10,
                format=camera.JPEG,
                fb_location=camera.PSRAM,
                flip=1,
                whitebalance=camera.WB_CLOUDY
            )
            # 成功则记录并跳出循环
            chosen_framesize = framesize
            set_w, set_h = CameraController.get_resolution(framesize)
            debug_log("✅ 摄像头初始化成功，分辨率: {}×{}".format(set_w, set_h),
                      level=LEVEL_INFO, module="app")
            break
        except Exception as e:
            debug_log("❌ 分辨率 {} 初始化失败: {}".format(res_name, e), level=LEVEL_WARNING, module="app")
            # 继续尝试下一个分辨率
            continue

    if cam is None:
        debug_log("❌ 所有分辨率尝试均失败，无法继续", level=LEVEL_ERROR, module="app")
        return

    # 2. 挂载 SD 卡（确保已就绪）
    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载，无法保存照片", level=LEVEL_ERROR, module="app")
        return

    # 3. 闪光灯预闪
    flash = get_flash(pin=4, on_value=1)
    flash.on()
    time.sleep_ms(200)

    # 4. 捕获图像
    try:
        buf = cam.capture()
    except Exception as e:
        debug_log("❌ 捕获失败: {}".format(e), level=LEVEL_ERROR, module="app")
        flash.off()
        cam.deinit()
        return
    finally:
        flash.off()

    if not buf:
        debug_log("❌ 捕获失败（无数据）", level=LEVEL_ERROR, module="app")
        cam.deinit()
        return

    # 5. 保存到 SD 卡
    filename = "/sd/photo_{}.jpg".format(int(time.time()))
    saved = sd.save_file(buf, filename)

    # 6. 从 JPEG 解析实际尺寸（用于确认实际输出）
    w_actual, h_actual = get_image_dimensions(buf)
    if w_actual == 0 or h_actual == 0 or w_actual > 10000 or h_actual > 10000:
        # 解析失败，使用设定尺寸（但可能是错误的）
        w_actual, h_actual = set_w, set_h
        debug_log("⚠️ 无法从JPEG解析实际尺寸，使用设定尺寸", level=LEVEL_WARNING, module="app")
    else:
        debug_log("实际图像尺寸 (JPEG解析): {}×{}".format(w_actual, h_actual), level=LEVEL_INFO, module="app")
        # 如果实际尺寸与设定不符，说明驱动降级了
        if w_actual != set_w or h_actual != set_h:
            debug_log("⚠️ 摄像头驱动将分辨率从 {}×{} 降级为 {}×{} (可能因内存不足)".format(
                set_w, set_h, w_actual, h_actual), level=LEVEL_WARNING, module="app")

    # 7. 输出结果
    if saved:
        debug_log("✅ 照片保存成功: {} (设定: {}×{}, 实际: {}×{}, {} bytes)".format(
            saved, set_w, set_h, w_actual, h_actual, len(buf)),
                  level=LEVEL_INFO, module="app")
    else:
        debug_log("❌ 保存失败", level=LEVEL_ERROR, module="app")

    # 8. 释放摄像头
    cam.deinit()
    debug_log("✅ 拍照完成", level=LEVEL_INFO, module="app")

if __name__ == "__main__":
    main()