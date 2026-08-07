"""
app.py - ESP32-CAM 简单拍照程序

执行一次拍照：初始化摄像头、闪光灯补光、捕获 JPEG、保存到 SD 卡。
适用于快速拍照或作为其他应用的基础调用。
"""
import time
import camera
from config import set_debug, debug_log
from camera_driver import reset_camera, get_camera
from flash import get_flash
from sd_card import get_sd_card

# 启用调试日志（可选）
set_debug(True)

def main():
    print("\n📷 ESP32-CAM 拍照程序启动")

    # 1. 重置摄像头，确保干净状态
    reset_camera()
    time.sleep_ms(200)

    # 2. 获取 SD 卡实例（确保已挂载）
    sd = get_sd_card()
    if not sd.mounted:
        print("❌ SD 卡未挂载，无法保存照片")
        return

    # 3. 获取摄像头并初始化（使用默认参数）
    cam = get_camera()
    if not cam.initialized:
        try:
            cam.init(
                framesize=camera.FRAME_XGA,
                quality=10,
                format=camera.JPEG,
                fb_location=camera.PSRAM,
                flip=1,
                whitebalance=camera.WB_CLOUDY
            )
            debug_log("Camera initialized", module="app")
        except Exception as e:
            print("❌ 摄像头初始化失败:", e)
            return

    # 4. 闪光灯预闪（可选）
    flash = get_flash(pin=4, on_value=1)
    flash.on()
    time.sleep_ms(200)  # 等待曝光稳定

    # 5. 捕获图像
    try:
        buf = cam.capture()
    except Exception as e:
        print("❌ 捕获失败:", e)
        flash.off()
        cam.deinit()
        return
    finally:
        flash.off()

    if not buf:
        print("❌ 捕获失败（无数据）")
        cam.deinit()
        return

    # 6. 保存到 SD 卡
    filename = "/sd/photo_{}.jpg".format(int(time.time()))
    saved = sd.save_file(buf, filename)
    if saved:
        print("✅ 照片保存成功: {} ({} bytes)".format(saved, len(buf)))
    else:
        print("❌ 保存失败")

    # 7. 释放摄像头
    cam.deinit()
    print("✅ 拍照完成")

if __name__ == "__main__":
    main()