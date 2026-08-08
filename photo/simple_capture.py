# photo/simple_capture.py
"""
简单降级拍照流程：
按指定的分辨率列表依次尝试初始化摄像头（自动降级），
拍照并保存，同时检测驱动是否降级了分辨率并输出日志。
"""
import time
import gc
import camera
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR
from camera_driver import reset_camera, get_camera, CameraController
from camera_driver.resolutions import get_name_by_value
from flash import get_flash
from sd_card import get_sd_card
from utils import get_image_dimensions


def simple_capture_with_downgrade(
    preferred_resolutions=None,
    quality=10,
    flash_pin=4,
    flash_on_value=1,
    sd_mount_point="/sd",
    whitebalance=camera.WB_CLOUDY,
    flip=1,
    fb_location=camera.PSRAM,
):
    """
    简单降级拍照流程：
    1. 按 preferred_resolutions 列表依次尝试初始化摄像头（从高到低）。
    2. 一旦成功，拍照并保存。
    3. 解析 JPEG 实际尺寸，检测是否被驱动降级。

    参数：
        preferred_resolutions (list): 首选分辨率列表（从高到低），默认为 QSXGA→UXGA→XGA→SVGA→VGA→QVGA。
        quality (int): JPEG 质量（10~63）。
        flash_pin (int): 闪光灯 GPIO 引脚。
        flash_on_value (int): 闪光灯点亮电平。
        sd_mount_point (str): SD 卡挂载点。
        whitebalance (int): 白平衡模式。
        flip (int): 上下翻转。
        fb_location (int): 帧缓冲区位置（PSRAM/DRAM）。

    返回：
        tuple: (saved_path, actual_width, actual_height, requested_width, requested_height, framesize)
               若失败，saved_path 为 None。
    """
    if preferred_resolutions is None:
        preferred_resolutions = [
            camera.FRAME_QSXGA,   # 2560x1920
            camera.FRAME_UXGA,    # 1600x1200
            camera.FRAME_XGA,     # 1024x768
            camera.FRAME_SVGA,    # 800x600
            camera.FRAME_VGA,     # 640x480
            camera.FRAME_QVGA,    # 320x240
        ]

    debug_log("📷 简单降级拍照流程启动", level=LEVEL_INFO, module="SimpleCapture")

    # ---------- 1. 尝试初始化摄像头 ----------
    cam = None
    chosen_framesize = None
    set_w = set_h = 0

    for framesize in preferred_resolutions:
        res_name = get_name_by_value(framesize) or "UNKNOWN"
        debug_log("尝试初始化分辨率: {} ({})".format(res_name, framesize), level=LEVEL_INFO, module="SimpleCapture")

        reset_camera()
        gc.collect()
        time.sleep_ms(300)

        try:
            cam = get_camera(
                framesize=framesize,
                quality=quality,
                format=camera.JPEG,
                fb_location=fb_location,
                flip=flip,
                whitebalance=whitebalance
            )
            chosen_framesize = framesize
            set_w, set_h = CameraController.get_resolution(framesize)
            debug_log("✅ 摄像头初始化成功，分辨率: {}×{}".format(set_w, set_h),
                      level=LEVEL_INFO, module="SimpleCapture")
            break
        except Exception as e:
            debug_log("❌ 分辨率 {} 初始化失败: {}".format(res_name, e), level=LEVEL_WARNING, module="SimpleCapture")
            continue

    if cam is None:
        debug_log("❌ 所有分辨率尝试均失败，无法继续", level=LEVEL_ERROR, module="SimpleCapture")
        return None, 0, 0, 0, 0, None

    # ---------- 2. 挂载 SD 卡 ----------
    sd = get_sd_card(mount_point=sd_mount_point)
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载，无法保存照片", level=LEVEL_ERROR, module="SimpleCapture")
        return None, 0, 0, 0, 0, chosen_framesize

    # ---------- 3. 闪光灯预闪 ----------
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    flash.on()
    time.sleep_ms(200)

    # ---------- 4. 捕获图像 ----------
    try:
        buf = cam.capture()
    except Exception as e:
        debug_log("❌ 捕获失败: {}".format(e), level=LEVEL_ERROR, module="SimpleCapture")
        flash.off()
        cam.deinit()
        return None, 0, 0, set_w, set_h, chosen_framesize
    finally:
        flash.off()

    if not buf:
        debug_log("❌ 捕获失败（无数据）", level=LEVEL_ERROR, module="SimpleCapture")
        cam.deinit()
        return None, 0, 0, set_w, set_h, chosen_framesize

    # ---------- 5. 保存到 SD 卡 ----------
    filename = "/sd/photo_{}.jpg".format(int(time.time()))
    saved_path = sd.save_file(buf, filename)

    # ---------- 6. 解析实际尺寸 ----------
    w_actual, h_actual = get_image_dimensions(buf)
    if w_actual == 0 or h_actual == 0 or w_actual > 10000 or h_actual > 10000:
        w_actual, h_actual = set_w, set_h
        debug_log("⚠️ 无法从JPEG解析实际尺寸，使用设定尺寸", level=LEVEL_WARNING, module="SimpleCapture")
    else:
        debug_log("实际图像尺寸 (JPEG解析): {}×{}".format(w_actual, h_actual), level=LEVEL_INFO, module="SimpleCapture")
        if w_actual != set_w or h_actual != set_h:
            debug_log("⚠️ 摄像头驱动将分辨率从 {}×{} 降级为 {}×{} (可能因内存不足)".format(
                set_w, set_h, w_actual, h_actual), level=LEVEL_WARNING, module="SimpleCapture")

    # ---------- 7. 输出结果 ----------
    if saved_path:
        debug_log("✅ 照片保存成功: {} (设定: {}×{}, 实际: {}×{}, {} bytes)".format(
            saved_path, set_w, set_h, w_actual, h_actual, len(buf)),
                  level=LEVEL_INFO, module="SimpleCapture")
    else:
        debug_log("❌ 保存失败", level=LEVEL_ERROR, module="SimpleCapture")

    cam.deinit()
    debug_log("✅ 拍照完成", level=LEVEL_INFO, module="SimpleCapture")

    return saved_path, w_actual, h_actual, set_w, set_h, chosen_framesize