# photo_capturer.py
from flash import Flash
from camera_controller import CameraController
from sd_card import SDCardManager
import time

class PhotoCapturer:
    """
    集成闪光灯、摄像头和 SD 卡，提供一键拍照保存功能。
    """
    def __init__(self, flash_pin=4, flash_on_value=0,
                 sd_mount_point="/sd", camera_params=None):
        self.flash = Flash(pin=flash_pin, on_value=flash_on_value)
        self.sd = SDCardManager(mount_point=sd_mount_point)
        # 默认摄像头参数（可覆盖）
        self.camera_params = camera_params or {}
        self.camera = None

    def setup_camera(self, **kwargs):
        """初始化摄像头，可传入覆盖参数"""
        # 合并默认参数
        params = self.camera_params.copy()
        params.update(kwargs)
        self.camera = CameraController()
        self.camera.init(**params)

    def take_photo(self, filename=None, pre_flash_delay=200,
                   post_flash_delay=0, auto_deinit=True):
        """
        执行完整的拍照流程：
          1. 打开闪光灯
          2. 等待曝光稳定
          3. 捕获图像
          4. 关闭闪光灯
          5. 保存到 SD 卡
        返回保存的文件路径，失败返回 None。
        """
        if self.camera is None:
            self.setup_camera()   # 使用默认参数

        # 开闪光灯
        self.flash.on()
        time.sleep_ms(pre_flash_delay)

        # 捕获
        buf = self.camera.capture()
        self.flash.off()        # 即使捕获失败也关灯
        if buf is None:
            print("Photo capture failed")
            if auto_deinit:
                self.camera.deinit()
            return None

        if post_flash_delay:
            time.sleep_ms(post_flash_delay)  # 可选额外延迟

        # 保存
        filepath = self.sd.save_file(buf, filename)

        if auto_deinit:
            self.camera.deinit()

        return filepath

    def cleanup(self):
        """释放所有资源"""
        if self.camera and self.camera.initialized:
            self.camera.deinit()
        self.flash.off()