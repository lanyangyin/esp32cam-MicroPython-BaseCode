# camera_driver/resolutions.py
"""
分辨率映射工具

提供摄像头所有支持的分辨率常量与其名称、尺寸的映射关系。
所有尺寸来自 ESP32 camera 驱动和传感器数据手册（OV3660/OV2640）。

主要功能：
    - get_resolution(framesize): 根据常量返回 (宽, 高)
    - get_name_by_value(framesize): 根据常量返回名称（如 "FRAME_XGA"）
    - list_resolutions(): 打印所有分辨率表格
    - is_resolution_supported(framesize): 检查分辨率是否在映射表中

设计上自动适配固件支持的分辨率（如 HQVGA 可能存在也可能不存在）。
"""
import camera  # type: ignore
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Resolutions")

# 所有支持的分辨率常量名称列表（按顺序）
RESOLUTION_NAMES = [
    "FRAME_96X96",     # 96x96
    "FRAME_QQVGA",     # 160x120
    "FRAME_QCIF",      # 176x144
    "FRAME_HQVGA",     # 240x176
    "FRAME_240X240",   # 240x240
    "FRAME_QVGA",      # 320x240
    "FRAME_CIF",       # 400x296
    "FRAME_HVGA",      # 480x320
    "FRAME_VGA",       # 640x480
    "FRAME_SVGA",      # 800x600
    "FRAME_XGA",       # 1024x768
    "FRAME_HD",        # 1280x720
    "FRAME_SXGA",      # 1280x1024
    "FRAME_UXGA",      # 1600x1200
    "FRAME_FHD",       # 1920x1080
    "FRAME_P_HD",      # 720x1280 (竖屏HD)
    "FRAME_P_3MP",     # 864x1536 (竖屏3MP)
    "FRAME_QXGA",      # 2048x1536
    "FRAME_QHD",       # 2560x1440
    "FRAME_WQXGA",     # 2560x1600
    "FRAME_P_FHD",     # 1080x1920 (竖屏FHD)
    "FRAME_QSXGA",     # 2560x1920
]

# 动态构建：名称 -> camera常量（只包含固件实际支持的常量）
RESOLUTION_MAP = {}
for name in RESOLUTION_NAMES:
    if hasattr(camera, name):
        RESOLUTION_MAP[name] = getattr(camera, name)
        _debug_log("Mapped {} -> {}".format(name, getattr(camera, name)))
    else:
        _debug_log("Warning: {} not supported".format(name))

# 固定尺寸映射（常量 -> (宽, 高)）
# 所有尺寸来自 ESP32 camera 驱动
RESOLUTION_SIZE = {
    camera.FRAME_96X96:   (96, 96),
    camera.FRAME_QQVGA:   (160, 120),
    camera.FRAME_QCIF:    (176, 144),
    camera.FRAME_HQVGA:   (240, 176),
    camera.FRAME_240X240: (240, 240),
    camera.FRAME_QVGA:    (320, 240),
    camera.FRAME_CIF:     (400, 296),
    camera.FRAME_HVGA:    (480, 320),
    camera.FRAME_VGA:     (640, 480),
    camera.FRAME_SVGA:    (800, 600),
    camera.FRAME_XGA:     (1024, 768),
    camera.FRAME_HD:      (1280, 720),
    camera.FRAME_SXGA:    (1280, 1024),
    camera.FRAME_UXGA:    (1600, 1200),
    camera.FRAME_FHD:     (1920, 1080),
    camera.FRAME_P_HD:    (720, 1280),
    camera.FRAME_P_3MP:   (864, 1536),
    camera.FRAME_QXGA:    (2048, 1536),
    camera.FRAME_QHD:     (2560, 1440),
    camera.FRAME_WQXGA:   (2560, 1600),
    camera.FRAME_P_FHD:   (1080, 1920),
    camera.FRAME_QSXGA:   (2560, 1920),
}


def get_resolution(framesize):
    """
    根据 framesize 常量返回 (宽度, 高度)。

    参数：
        framesize (int): 摄像头分辨率常量（如 camera.FRAME_XGA）。

    返回：
        tuple: (width, height)，若未找到则返回 (None, None)。
    """
    return RESOLUTION_SIZE.get(framesize, (None, None))


def get_name_by_value(framesize):
    """
    根据常量值查找对应的分辨率名称。

    参数：
        framesize (int): 分辨率常量值。

    返回：
        str or None: 名称（如 "FRAME_XGA"），若未找到则返回 None。
    """
    for name, val in RESOLUTION_MAP.items():
        if val == framesize:
            return name
    return None


def list_resolutions():
    """打印所有可用的分辨率及其名称、常量和尺寸（表格形式）。"""
    print("Available camera resolutions:")
    print("┌─────────────┬────────────┬──────────┐")
    print("│   Name      │  Constant  │  Size    │")
    print("├─────────────┼────────────┼──────────┤")
    for name in RESOLUTION_NAMES:
        if name in RESOLUTION_MAP:
            val = RESOLUTION_MAP[name]
            w, h = get_resolution(val)
            size_str = "{}×{}".format(w, h) if w else "unknown"
            print("│ {:<11} │ {:<10} │ {:<8} │".format(name, val, size_str))
    print("└─────────────┴────────────┴──────────┘")


def is_resolution_supported(framesize):
    """检查分辨率是否在映射表中。"""
    w, h = get_resolution(framesize)
    return w is not None and h is not None