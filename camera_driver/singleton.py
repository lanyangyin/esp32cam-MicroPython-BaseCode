# camera_driver/singleton.py
"""
摄像头单例管理

确保整个程序中只有一个摄像头控制器实例（`CameraController`）。
提供获取实例、初始化参数传递、重置、可用性检查等功能。

设计目的：
    - 避免重复初始化摄像头，节省资源
    - 方便全局共享摄像头状态
    - 支持在初始化失败时自动重试
    - 提供实例可用性检查，便于外部判断
    - 支持带参数重新初始化（切换分辨率/配置）

核心函数：
    - get_camera(**init_kwargs): 获取或重新初始化摄像头实例
      * 若传入参数，强制重新初始化（释放旧实例，用新参数创建）
      * 若不传参数，返回现有可用实例（若存在），否则创建默认实例（使用 VGA 等保守参数）
    - reset_camera(): 强制释放并重置单例（用于调试或重新配置）
    - is_camera_available(): 判断摄像头实例是否存在且已初始化
"""
import time
import camera  # type: ignore
from .controller import CameraController
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="CameraCtrl")


_camera_instance = None


def is_camera_available():
    """
    判断摄像头实例是否存在并且可用（已初始化）。

    返回：
        bool: 如果实例存在且 `initialized` 为 True，返回 True；否则返回 False。

    典型用法：
        if not is_camera_available():
            cam = get_camera(framesize=camera.FRAME_XGA)
        else:
            cam = get_camera()  # 直接获取已有实例
    """
    global _camera_instance
    if _camera_instance is None:
        return False
    return _camera_instance.initialized


def get_camera(**init_kwargs):
    """
    获取摄像头控制器单例对象。

    行为逻辑（核心变更）：
        - **如果传入了参数（例如 `framesize=camera.FRAME_XGA`）**：
            强制重新初始化摄像头。会先释放当前实例（`reset_camera()`），然后用新参数创建实例。
            这用于切换分辨率或更改配置。
        - **如果不传入参数**：
            返回当前已有的可用实例（若存在且已初始化）。若没有可用实例，则创建一个默认实例（使用保守参数：VGA, 10MHz, PSRAM）。

    若初始化失败，会先尝试释放硬件（`camera.deinit()`），然后重试一次。
    若重试仍失败，抛出异常。

    参数：
        **init_kwargs: 传递给 `CameraController.init()` 的关键字参数，
            包括 framesize、quality、format、flip、whitebalance 等。
            具体参数说明见 `CameraController.init`。

    返回：
        CameraController: 单例实例。

    异常：
        若初始化失败（包括重试），抛出异常。
    """
    global _camera_instance

    # 如果传入了参数，强制重新初始化（释放旧实例，用新参数创建）
    if init_kwargs:
        reset_camera()  # 释放现有实例（如果有）
        _debug_log("Reinitializing camera with new params: {}".format(init_kwargs))
    else:
        # 无参数，尝试返回已有实例
        if _camera_instance is not None and _camera_instance.initialized:
            _debug_log("Return existing camera instance (available)")
            return _camera_instance

    # 创建新实例（无可用实例或强制重新初始化）
    _debug_log("Creating camera instance...")
    try:
        _camera_instance = CameraController()
        # 如果没有传入参数，使用保守默认参数（VGA 更稳定）
        if not init_kwargs:
            _debug_log("Using conservative default settings (VGA)")
            _camera_instance.init(
                framesize=camera.FRAME_VGA,
                quality=10,
                format=camera.JPEG,
                fb_location=camera.PSRAM,
                xclk_freq=camera.XCLK_10MHz,
                flip=1,
                mirror=0,
                saturation=0,
                brightness=0,
                contrast=0,
                whitebalance=camera.WB_CLOUDY,
                effect=camera.EFFECT_NONE
            )
        else:
            _camera_instance.init(**init_kwargs)
        _debug_log("Camera initialized successfully")
        return _camera_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        # 强制释放硬件
        try:
            camera.deinit()
        except:
            pass
        # 清除可能残留的实例
        if _camera_instance is not None:
            try:
                _camera_instance.deinit()
            except:
                pass
            _camera_instance = None
        # 重试一次
        try:
            _camera_instance = CameraController()
            if not init_kwargs:
                _camera_instance.init(
                    framesize=camera.FRAME_VGA,
                    quality=10,
                    format=camera.JPEG,
                    fb_location=camera.PSRAM,
                    xclk_freq=camera.XCLK_10MHz,
                    flip=1,
                    mirror=0,
                    saturation=0,
                    brightness=0,
                    contrast=0,
                    whitebalance=camera.WB_CLOUDY,
                    effect=camera.EFFECT_NONE
                )
            else:
                _camera_instance.init(**init_kwargs)
            _debug_log("Camera initialized on retry")
            return _camera_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise


def reset_camera():
    """
    强制释放并重置摄像头单例。

    无论实例是否存在，都会强制调用 `camera.deinit()` 确保硬件释放，
    然后清除单例，以便下次调用 `get_camera()` 时重新创建。

    该函数常用于：
        - 调试时重置摄像头状态
        - 切换分辨率前彻底释放资源
        - 从错误状态中恢复
    """
    global _camera_instance
    try:
        camera.deinit()
        _debug_log("Force camera.deinit() called")
    except:
        pass
    if _camera_instance is not None:
        _debug_log("Resetting camera singleton")
        try:
            _camera_instance.deinit()
        except:
            pass
        _camera_instance = None
    # 硬件需要时间复位，建议至少 200ms
    time.sleep_ms(200)


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug

    set_debug(True)

    print("\n=== 摄像头单例管理测试 ===\n")

    # 测试 1：首次获取实例（无参数，应创建默认实例，使用 VGA）
    print("测试 1：首次获取实例（无参数）")
    cam1 = get_camera()
    print("cam1 是否可用:", is_camera_available())
    print("cam1 地址:", id(cam1))

    # 测试 2：再次获取实例（无参数，应返回同一实例）
    print("\n测试 2：再次获取实例（无参数，应返回同一实例）")
    cam2 = get_camera()
    print("cam1 与 cam2 是否相同:", cam1 is cam2)

    # 测试 3：带参数获取（应强制重新初始化，切换分辨率）
    print("\n测试 3：带参数获取（应强制重新初始化，切换分辨率）")
    cam3 = get_camera(framesize=camera.FRAME_XGA, quality=15)
    print("cam3 是否可用:", is_camera_available())
    print("cam3 地址:", id(cam3))
    print("cam3 与 cam1 是否相同:", cam3 is cam1)  # False

    # 测试 4：重置摄像头
    print("\n测试 4：重置摄像头")
    reset_camera()
    print("重置后是否可用:", is_camera_available())

    # 测试 5：重新获取实例（无参数，应创建新默认实例）
    print("\n测试 5：重新获取实例（无参数）")
    cam4 = get_camera()
    print("cam4 是否可用:", is_camera_available())
    print("cam4 地址:", id(cam4))

    print("\n测试完成")