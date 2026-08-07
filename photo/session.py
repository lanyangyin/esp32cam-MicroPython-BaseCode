# photo/session.py
"""资源管理（setup/cleanup）"""
from camera_driver import get_camera, reset_camera
from flash import get_flash, reset_flash
from sd_card import get_sd_card, reset_sd_card
import time

def cleanup_all():
    """释放所有硬件资源（摄像头、闪光灯、SD卡）"""
    cam = get_camera()
    if cam.initialized:
        cam.deinit()
    flash = get_flash()
    flash.off()
    # SD 卡不强制卸载，保留挂载

def reset_all():
    """重置所有单例（用于测试）"""
    reset_camera()
    reset_flash()
    reset_sd_card()
    time.sleep_ms(200)