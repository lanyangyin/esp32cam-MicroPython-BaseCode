"""
app.py - ESP32-CAM 简单拍照程序

执行一次拍照：初始化摄像头、闪光灯补光、捕获 JPEG、保存到 SD 卡。
适用于快速拍照或作为其他应用的基础调用。
"""
import time
import camera
from config import set_debug, debug_log, LEVEL_INFO, LEVEL_ERROR
from camera_driver import reset_camera, get_camera, CameraController
from flash import get_flash
from sd_card import get_sd_card

# 启用调试日志
set_debug(True)

# 固定拍照分辨率（可在此修改）
FRAMESIZE = camera.FRAME_XGA

def main():
    debug_log("📷 ESP32-CAM 拍照程序启动", level=LEVEL_INFO, module="app")

    # 1. 重置摄像头，确保干净状态
    reset_camera()
    time.sleep_ms(200)

    # 2. 获取 SD 卡实例（确保已挂载）
    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载，无法保存照片", level=LEVEL_ERROR, module="app")
        return

    # 3. 获取摄像头并初始化
    cam = get_camera()
    if not cam.initialized:
        try:
            cam.init(
                framesize=FRAMESIZE,
                quality=10,
                format=camera.JPEG,
                fb_location=camera.PSRAM,
                flip=1,
                whitebalance=camera.WB_CLOUDY
            )
            debug_log("Camera initialized with FRAMESIZE={}".format(FRAMESIZE), level=LEVEL_INFO, module="app")
        except Exception as e:
            debug_log("❌ 摄像头初始化失败: {}".format(e), level=LEVEL_ERROR, module="app")
            return

    # 4. 闪光灯预闪
    flash = get_flash(pin=4, on_value=1)
    flash.on()
    time.sleep_ms(200)

    # 5. 捕获图像
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

    # 6. 保存到 SD 卡
    filename = "/sd/photo_{}.jpg".format(int(time.time()))
    saved = sd.save_file(buf, filename)

    # 获取分辨率
    w, h = CameraController.get_resolution(FRAMESIZE)
    if w is None or h is None:
        w, h = 0, 0

    if saved:
        debug_log("✅ 照片保存成功: {} ({}×{}, {} bytes)".format(saved, w, h, len(buf)),
                  level=LEVEL_INFO, module="app")
    else:
        debug_log("❌ 保存失败", level=LEVEL_ERROR, module="app")

    # 7. 释放摄像头
    cam.deinit()
    debug_log("✅ 拍照完成", level=LEVEL_INFO, module="app")

if __name__ == "__main__":
    main()