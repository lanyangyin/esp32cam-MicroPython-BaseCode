"""
app.py - ESP32-CAM 简单拍照程序
"""
import time
import camera
from config import set_debug, debug_log, LEVEL_INFO, LEVEL_ERROR, LEVEL_WARNING
from camera_driver import reset_camera, get_camera, CameraController
from camera_driver.resolutions import get_name_by_value, get_resolution
from flash import get_flash
from sd_card import get_sd_card

set_debug(True)

# 固定拍照分辨率（可在此修改）
FRAMESIZE = camera.FRAME_VGA  # 2560x1920

def main():
    debug_log("📷 ESP32-CAM 拍照程序启动", level=LEVEL_INFO, module="app")

    # 打印请求的分辨率信息
    req_name = get_name_by_value(FRAMESIZE) or "UNKNOWN"
    debug_log("Requested FRAMESIZE = {} ({})".format(req_name, FRAMESIZE), level=LEVEL_INFO, module="app")

    reset_camera()
    time.sleep_ms(200)

    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载，无法保存照片", level=LEVEL_ERROR, module="app")
        return

    # 获取摄像头实例，并直接传入初始化参数
    try:
        cam = get_camera(
            framesize=FRAMESIZE,
            quality=10,
            format=camera.JPEG,
            fb_location=camera.PSRAM,
            flip=1,
            whitebalance=camera.WB_CLOUDY
        )
        set_w, set_h = CameraController.get_resolution(FRAMESIZE)
        debug_log("Camera initialized, requested resolution: {}×{}".format(set_w, set_h),
                  level=LEVEL_INFO, module="app")
    except Exception as e:
        debug_log("❌ 摄像头初始化失败: {}".format(e), level=LEVEL_ERROR, module="app")
        return

    flash = get_flash(pin=4, on_value=1)
    flash.on()
    time.sleep_ms(200)

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

    filename = "/sd/photo_{}.jpg".format(int(time.time()))
    saved = sd.save_file(buf, filename)

    # 获取实际帧大小（摄像头驱动可能因内存限制降级）
    try:
        actual_fs = camera.framesize(0)  # 获取当前帧大小
        actual_name = get_name_by_value(actual_fs) or "UNKNOWN"
        w_actual, h_actual = get_resolution(actual_fs)
        if w_actual is None or h_actual is None:
            w_actual, h_actual = set_w, set_h
            debug_log("⚠️ 无法映射实际帧大小 {}，使用请求尺寸".format(actual_fs), level=LEVEL_WARNING, module="app")
        else:
            debug_log("Actual framesize: {} ({}×{})".format(actual_name, w_actual, h_actual),
                      level=LEVEL_INFO, module="app")
    except Exception as e:
        debug_log("⚠️ 获取实际帧大小失败: {}，使用请求尺寸".format(e), level=LEVEL_WARNING, module="app")
        w_actual, h_actual = set_w, set_h

    if saved:
        debug_log("✅ 照片保存成功: {} (设定: {}×{}, 实际: {}×{}, {} bytes)".format(
            saved, set_w, set_h, w_actual, h_actual, len(buf)),
                  level=LEVEL_INFO, module="app")
    else:
        debug_log("❌ 保存失败", level=LEVEL_ERROR, module="app")

    cam.deinit()
    debug_log("✅ 拍照完成", level=LEVEL_INFO, module="app")

if __name__ == "__main__":
    main()