# photo/manual_photo_taker.py
"""
手动控制闪光灯的拍照功能（无自动决策）。
"""
import time
import gc
import camera
from camera_driver import reset_camera, capture_image, get_camera, CameraController
from flash import get_flash
from sd_card import get_sd_card
from utils import get_image_dimensions
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR


def take_photo_manual(
    use_flash=False,
    framesize=camera.FRAME_XGA,
    quality=10,
    flash_pin=4,
    flash_on_value=1,
    sd_mount_point="/sd",
    whitebalance=camera.WB_CLOUDY,
    flip=1,
    fb_location=camera.PSRAM,
    pre_flash_delay=200,
):
    """
    手动控制闪光灯拍照（不进行亮度分析或自动决策）。

    Args:
        use_flash (bool): True 开启闪光灯，False 关闭。
        framesize (int): 照片分辨率。
        quality (int): JPEG 质量（10~63）。
        flash_pin (int): 闪光灯 GPIO 引脚。
        flash_on_value (int): 闪光灯点亮电平。
        sd_mount_point (str): SD 卡挂载点。
        whitebalance (int): 白平衡模式。
        flip (int): 上下翻转。
        fb_location (int): 帧缓冲区位置。
        pre_flash_delay (int): 闪光灯开启后到拍摄的延时（毫秒）。

    Returns:
        tuple: (saved_path, actual_width, actual_height)
               若失败，saved_path 为 None。
    """
    debug_log("手动拍照启动", level=LEVEL_INFO, module="ManualPhotoTaker")
    print("📷 手动拍照 (闪光灯: {})".format("开" if use_flash else "关"))

    # 初始化摄像头
    reset_camera()
    gc.collect()
    time.sleep_ms(200)

    cam = get_camera(
        framesize=framesize,
        quality=quality,
        format=camera.JPEG,
        fb_location=fb_location,
        flip=flip,
        whitebalance=whitebalance
    )
    if cam is None:
        debug_log("摄像头初始化失败", level=LEVEL_ERROR, module="ManualPhotoTaker")
        return None, 0, 0

    # 挂载 SD 卡
    sd = get_sd_card(mount_point=sd_mount_point)
    if not sd.mounted:
        debug_log("SD 卡未挂载", level=LEVEL_ERROR, module="ManualPhotoTaker")
        cam.deinit()
        return None, 0, 0

    # 闪光灯控制
    flash = get_flash(pin=flash_pin, on_value=flash_on_value)
    if use_flash:
        flash.on()
        time.sleep_ms(pre_flash_delay)
    else:
        flash.off()

    # 捕获
    try:
        buf = cam.capture()
    except Exception as e:
        debug_log("捕获异常: {}".format(e), level=LEVEL_ERROR, module="ManualPhotoTaker")
        flash.off()
        cam.deinit()
        return None, 0, 0
    finally:
        flash.off()

    if not buf:
        debug_log("捕获无数据", level=LEVEL_ERROR, module="ManualPhotoTaker")
        cam.deinit()
        return None, 0, 0

    # 保存
    filename = "/sd/photo_manual_{}.jpg".format(int(time.time()))
    saved_path = sd.save_file(buf, filename)
    cam.deinit()

    # 解析尺寸
    w, h = get_image_dimensions(buf)
    if w == 0 or h == 0:
        w, h = CameraController.get_resolution(framesize)

    if saved_path:
        debug_log("✅ 照片保存成功: {} ({}×{}, {} bytes)".format(
            saved_path, w, h, len(buf)), level=LEVEL_INFO, module="ManualPhotoTaker")
        print("  保存至: {} ({}x{})".format(saved_path, w, h))
    else:
        debug_log("保存失败", level=LEVEL_ERROR, module="ManualPhotoTaker")
        print("  保存失败")

    return saved_path, w, h


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    print("手动拍照测试（需硬件）")
    # 示例：关闭闪光灯拍照
    saved, w, h = take_photo_manual(use_flash=False, framesize=camera.FRAME_VGA)
    if saved:
        print("成功")
    else:
        print("失败")