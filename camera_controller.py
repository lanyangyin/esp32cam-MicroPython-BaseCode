# camera_controller.py
# pyrefly: ignore [missing-import]
import camera
import time


class CameraController:
    """
    ESP32-CAM 摄像头控制封装类。
    提供初始化、参数配置、图像捕获和资源释放功能。
    所有摄像头相关操作均通过此类完成，降低与底层 `camera` 模块的耦合。
    """

    def __init__(self):
        """初始化控制器状态，摄像头默认未初始化。"""
        self.initialized = False

    def init(self, framesize=camera.FRAME_XGA, quality=10,
             format=camera.JPEG, fb_location=camera.PSRAM,
             xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
             saturation=0, brightness=0, contrast=0,
             whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
        """
        初始化摄像头并应用图像参数。

        参数：
            framesize (int): 图像分辨率，如 camera.FRAME_XGA, camera.FRAME_VGA 等。
            quality (int): JPEG 质量（仅对 JPEG 格式有效），取值范围 10~63，数值越小画质越高（文件越大）。
            format (int): 图像格式，camera.JPEG 或 camera.GRAYSCALE。
            fb_location (int): 帧缓冲区位置，camera.PSRAM 或 camera.DRAM。
            xclk_freq (int): 主时钟频率，camera.XCLK_10MHz 或 camera.XCLK_20MHz。
            flip (int): 上下翻转，1 翻转，0 不翻转。
            mirror (int): 左右镜像，1 镜像，0 不镜像。
            saturation (int): 饱和度，取值范围 -2 ~ 2，0 为正常。
            brightness (int): 亮度，取值范围 -2 ~ 2，0 为正常。
            contrast (int): 对比度，取值范围 -2 ~ 2，0 为正常。
            whitebalance (int): 白平衡模式，如 camera.WB_CLOUDY, camera.WB_SUNNY 等。
            effect (int): 特效模式，如 camera.EFFECT_NONE, camera.EFFECT_BW 等。

        异常：
            若初始化失败，抛出异常并打印错误信息。
        """
        if self.initialized:
            self.deinit()  # 若已初始化，先释放

        try:
            camera.init(0,
                        format=format,
                        fb_location=fb_location,
                        framesize=framesize,
                        xclk_freq=xclk_freq)
        except Exception as e:
            print("Camera init failed:", e)
            raise

        # 应用图像调节参数
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
        """
        捕获一帧图像。

        返回：
            bytes: 图像数据（JPEG 或 GRAYSCALE 字节流），若捕获失败则返回 None。
        异常：
            若摄像头未初始化，抛出 RuntimeError。
        """
        if not self.initialized:
            raise RuntimeError("Camera not initialized")
        buf = camera.capture()
        if buf is None:
            print("Capture failed")
        return buf

    def deinit(self):
        """释放摄像头资源，关闭摄像头设备。"""
        if self.initialized:
            camera.deinit()
            self.initialized = False
            print("Camera deinitialized")

    @staticmethod
    def get_resolution(framesize):
        """
        根据分辨率常量返回图像宽度和高度。

        参数：
            framesize (int): 摄像头分辨率常量（如 camera.FRAME_XGA）。

        返回：
            tuple: (宽度, 高度)，若未找到对应分辨率则返回 (640, 480) 作为默认值。
        """
        res_map = {
            camera.FRAME_QQVGA: (160, 120),
            camera.FRAME_QVGA: (320, 240),
            camera.FRAME_VGA: (640, 480),
            camera.FRAME_XGA: (1024, 768),
            camera.FRAME_SVGA: (800, 600),
            camera.FRAME_UXGA: (1600, 1200),
        }
        return res_map.get(framesize, (640, 480))  # 默认 VGA