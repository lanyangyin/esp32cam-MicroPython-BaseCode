"""
camera_resolutions.py - 摄像头分辨率映射工具

本模块提供摄像头分辨率常量的名称、值和尺寸的对应关系。

核心功能：
    1. 动态构建分辨率映射表：从 camera 模块读取支持的常量
    2. 分辨率尺寸查询：get_resolution(framesize) 返回 (宽, 高)
    3. 名称反向查询：get_name_by_value(framesize) 返回常量名称
    4. 列表打印：list_resolutions() 输出表格

设计思路：
    - 自动适配固件支持的分辨率（如 HQVGA 可能存在也可能不存在）
    - 提供统一的尺寸查询接口，避免在多个模块中重复定义

依赖关系：
    - camera: 摄像头模块（提供分辨率常量）
    - config: 调试开关

典型用法：
    import camera_resolutions as res
    w, h = res.get_resolution(camera.FRAME_XGA)
    print(f"XGA 尺寸: {w}x{h}")
    res.list_resolutions()
"""

import camera  # type: ignore

from config import DEBUG


def _debug_log(msg):
    if DEBUG:
        print("[Resolutions] " + msg)


# ---------- 分辨率常量名称列表 ----------
RESOLUTION_NAMES = [
    "FRAME_QQVGA",  # 160x120
    "FRAME_HQVGA",  # 240x160（部分固件可能不支持）
    "FRAME_QVGA",   # 320x240
    "FRAME_VGA",    # 640x480
    "FRAME_SVGA",   # 800x600
    "FRAME_XGA",    # 1024x768
    "FRAME_UXGA",   # 1600x1200
]

# ---------- 动态构建：名称 -> camera常量 ----------
RESOLUTION_MAP = {}
for name in RESOLUTION_NAMES:
    if hasattr(camera, name):
        RESOLUTION_MAP[name] = getattr(camera, name)
        _debug_log("Mapped {} -> {}".format(name, getattr(camera, name)))
    else:
        _debug_log("Warning: {} not supported".format(name))

# ---------- 固定尺寸映射（常量 -> (宽, 高)） ----------
RESOLUTION_SIZE = {
    camera.FRAME_QQVGA: (160, 120),
    camera.FRAME_QVGA:  (320, 240),
    camera.FRAME_VGA:   (640, 480),
    camera.FRAME_SVGA:  (800, 600),
    camera.FRAME_XGA:   (1024, 768),
    camera.FRAME_UXGA:  (1600, 1200),
}
if hasattr(camera, "FRAME_HQVGA"):
    RESOLUTION_SIZE[camera.FRAME_HQVGA] = (240, 160)
    _debug_log("Added HQVGA size")

# ---------- 工具函数 ----------
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
        str: 名称（如 "FRAME_XGA"），若未找到则返回 None。
    """
    for name, val in RESOLUTION_MAP.items():
        if val == framesize:
            return name
    return None


def list_resolutions():
    """
    打印所有可用的分辨率及其名称、常量和尺寸。
    直接调用此函数会在控制台输出表格。
    """
    print("Available camera resolutions:")
    print("┌─────────────┬────────────┬──────────┐")
    print("│   Name      │  Constant  │  Size    │")
    print("├─────────────┼────────────┼──────────┤")
    for name in RESOLUTION_NAMES:
        if name in RESOLUTION_MAP:
            val = RESOLUTION_MAP[name]
            w, h = get_resolution(val)
            size_str = f"{w}×{h}" if w else "unknown"
            print(f"│ {name:<11} │ {val:<10} │ {size_str:<8} │")
    print("└─────────────┴────────────┴──────────┘")


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    print("\n--- camera_resolutions 模块测试 ---")
    start = time.ticks_ms()
    list_resolutions()
    # 测试单个查询
    print("\n查询 VGA 尺寸:", get_resolution(camera.FRAME_VGA))
    print("查询 XGA 名称:", get_name_by_value(camera.FRAME_XGA))
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))