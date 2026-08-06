# camera_controller.py
# pyrefly: ignore [missing-import]
import camera
import time

class CameraController:
    """
    ESP32-CAM 摄像头控制封装。
    支持初始化、参数调节、捕获 JPEG。
    """
    def __init__(self):
        self.initialized = False

    def init(self, framesize=camera.FRAME_XGA, quality=10,
             format=camera.JPEG, fb_location=camera.PSRAM,
             xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
             saturation=0, brightness=0, contrast=0,
             whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
        """
        初始化摄像头并应用常用参数。
        可传入分辨率、质量、翻转、白平衡等。
        """
        if self.initialized:
            self.deinit()
        try:
            camera.init(0,
                        format=format,
                        fb_location=fb_location,
                        framesize=framesize,
                        xclk_freq=xclk_freq)
        except Exception as e:
            print("Camera init failed:", e)
            raise

        # 应用图像调节
        camera.flip(flip)
        camera.mirror(mirror)
        camera.saturation(saturation)
        camera.brightness(brightness)
        camera.contrast(contrast)
        camera.whitebalance(whitebalance)
        camera.speffect(effect)
        camera.quality(quality)

        self.initialized = True
        self.framesize = framesize
        self.quality = quality
        print("Camera initialized with framesize={}, quality={}".format(framesize, quality))

    def capture(self):
        """捕获一张 JPEG 图像，返回 bytes 数据，若失败返回 None"""
        if not self.initialized:
            raise RuntimeError("Camera not initialized")
        buf = camera.capture()
        if buf is None:
            print("Capture failed")
        return buf

    def deinit(self):
        """释放摄像头资源"""
        if self.initialized:
            camera.deinit()
            self.initialized = False
            print("Camera deinitialized")

    @staticmethod
    def get_resolution(framesize):
        """根据 framesize 枚举返回 (宽度, 高度)"""
        # 常用分辨率映射（可根据需要补充）
        res_map = {
            camera.FRAME_QQVGA: (160, 120),
            camera.FRAME_QVGA: (320, 240),
            camera.FRAME_VGA: (640, 480),
            camera.FRAME_XGA: (1024, 768),
            camera.FRAME_SVGA: (800, 600),
            camera.FRAME_UXGA: (1600, 1200),  # 部分型号可能不支持
        }
        return res_map.get(framesize, (640, 480))  # 默认 VGA