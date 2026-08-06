# camera_controller.py
# pyrefly: ignore [missing-import]
import camera
import time
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[CameraCtrl] " + msg)

# ---------- 单例管理 ----------
_camera_instance = None

def get_camera(**init_kwargs):
    """
    获取摄像头控制器单例对象。
    第一次调用时创建实例并调用 init(**init_kwargs) 初始化，
    后续调用返回同一实例（忽略新传入的参数）。
    若初始化失败，先尝试释放再重试。

    参数：
        **init_kwargs: 传递给 CameraController.init() 的关键字参数。

    返回：
        CameraController: 单例实例。
    """
    global _camera_instance
    if _camera_instance is not None:
        _debug_log("Return existing camera instance")
        return _camera_instance

    _debug_log("Creating camera instance...")
    try:
        _camera_instance = CameraController()
        _camera_instance.init(**init_kwargs)
        _debug_log("Camera initialized successfully")
        return _camera_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        if _camera_instance is not None:
            try:
                _camera_instance.deinit()
            except:
                pass
            _camera_instance = None
        # 重试
        try:
            _camera_instance = CameraController()
            _camera_instance.init(**init_kwargs)
            _debug_log("Camera initialized on retry")
            return _camera_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise

def reset_camera():
    """强制释放并重置摄像头单例。"""
    global _camera_instance
    if _camera_instance is not None:
        _debug_log("Resetting camera singleton")
        try:
            _camera_instance.deinit()
        except:
            pass
        _camera_instance = None

# ---------- 基础捕获函数（不涉及闪光灯） ----------
def capture_image(framesize=camera.FRAME_XGA, quality=10,
                  format=camera.JPEG, fb_location=camera.PSRAM,
                  xclk_freq=camera.XCLK_10MHz, flip=1, mirror=0,
                  saturation=0, brightness=0, contrast=0,
                  whitebalance=camera.WB_CLOUDY, effect=camera.EFFECT_NONE):
    """
    基础拍照函数：初始化摄像头（若未初始化），捕获一帧图像，并返回 JPEG 数据。
    不涉及闪光灯控制，适用于纯图像采集。
    注意：此函数使用单例摄像头，若摄像头已初始化，会先 deinit 再重新 init（避免参数冲突）。
    若不想重新初始化，请直接使用 get_camera() 并自行调用 init/capture。

    参数同 CameraController.init()。

    返回：
        bytes: JPEG 图像数据，失败返回 None。
    """
    cam = get_camera()
    if cam.initialized:
        _debug_log("capture_image: deinit existing camera")
        cam.deinit()
    _debug_log("capture_image: initializing camera...")
    cam.init(framesize=framesize, quality=quality, format=format,
             fb_location=fb_location, xclk_freq=xclk_freq,
             flip=flip, mirror=mirror, saturation=saturation,
             brightness=brightness, contrast=contrast,
             whitebalance=whitebalance, effect=effect)
    _debug_log("capture_image: capturing...")
    buf = cam.capture()
    cam.deinit()
    _debug_log("capture_image: done, size={}".format(len(buf) if buf else 0))
    return buf

# ---------- CameraController 类 ----------
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
        内部包含重试机制，失败时会尝试重新初始化最多 3 次。

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
        max_retries = 3
        retry_delay = 150  # 毫秒
        last_exception = None

        for attempt in range(max_retries):
            if self.initialized:
                _debug_log("init: deinit existing (attempt {})".format(attempt + 1))
                self.deinit()

            _debug_log("init: calling camera.init() with framesize={} (attempt {})".format(framesize, attempt + 1))
            try:
                camera.init(0,
                            format=format,
                            fb_location=fb_location,
                            framesize=framesize,
                            xclk_freq=xclk_freq)
            except Exception as e:
                _debug_log("camera.init failed: {}".format(e))
                last_exception = e
                if attempt < max_retries - 1:
                    _debug_log("Retrying in {} ms...".format(retry_delay))
                    time.sleep_ms(retry_delay)
                    continue
                else:
                    raise  # 最后一次失败，抛出异常
            else:
                # 成功，跳出重试循环
                break

        # 应用图像调节参数
        _debug_log("Applying image settings...")
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
        _debug_log("Camera initialized with framesize={}, quality={}".format(framesize, quality))

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
        _debug_log("capture: calling camera.capture()")
        buf = camera.capture()
        if buf is None:
            _debug_log("capture: failed")
        else:
            _debug_log("capture: success, size={}".format(len(buf)))
        return buf

    def deinit(self):
        """释放摄像头资源，关闭摄像头设备。"""
        if self.initialized:
            _debug_log("deinit: calling camera.deinit()")
            camera.deinit()
            self.initialized = False
            _debug_log("Camera deinitialized")

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
        return res_map.get(framesize, (640, 480))

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- CameraController 模块测试 ---")
    start = time.ticks_ms()

    # 测试单例
    c1 = get_camera()
    c2 = get_camera()
    print("单例验证: c1 is c2 =", c1 is c2)

    # 测试基本捕获（注意：实际运行需要摄像头硬件）
    try:
        print("尝试捕获一张 JPEG 图像（分辨率 VGA）...")
        img = capture_image(framesize=camera.FRAME_VGA, quality=15)
        if img:
            print("捕获成功，图像大小: {} bytes".format(len(img)))
        else:
            print("捕获失败（可能无摄像头或硬件问题）")
    except Exception as e:
        print("捕获异常:", e)

    # 重置
    reset_camera()
    c3 = get_camera()
    print("重置后新实例:", c3 is not c1)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))