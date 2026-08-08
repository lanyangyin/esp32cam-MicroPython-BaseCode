# photo/resource_manager.py
"""
硬件资源管理（摄像头、闪光灯、SD卡）的清理与重置。
"""
from camera_driver import get_camera, reset_camera
from flash import get_flash, reset_flash
from sd_card import get_sd_card, reset_sd_card
import time


def cleanup_resources():
    """
    释放所有硬件资源（摄像头、闪光灯）。
    SD 卡保持挂载，不做卸载。
    """
    cam = get_camera()
    if cam.initialized:
        cam.deinit()
    flash = get_flash()
    flash.off()


def reset_resources():
    """重置所有单例（用于测试或强制重新初始化）。"""
    reset_camera()
    reset_flash()
    reset_sd_card()
    time.sleep_ms(200)


# ---------- 测试入口 ----------
if __name__ == "__main__":
    print("资源管理器测试：清理资源")
    cleanup_resources()
    print("重置资源")
    reset_resources()
    print("完成")