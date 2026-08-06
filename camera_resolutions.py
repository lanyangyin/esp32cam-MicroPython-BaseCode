# camera_resolutions.py
import camera

# ---------- 1. 分辨率常量名称列表 ----------
RESOLUTION_NAMES = [
    "FRAME_QQVGA",  # 160x120
    "FRAME_HQVGA",  # 240x160（部分固件可能不支持）
    "FRAME_QVGA",  # 320x240
    "FRAME_VGA",  # 640x480
    "FRAME_SVGA",  # 800x600
    "FRAME_XGA",  # 1024x768
    "FRAME_UXGA",  # 1600x1200
]

# ---------- 2. 动态构建：名称 -> camera常量 ----------
RESOLUTION_MAP = {}
for name in RESOLUTION_NAMES:
    if hasattr(camera, name):
        RESOLUTION_MAP[name] = getattr(camera, name)

# ---------- 3. 固定尺寸映射（常量 -> (宽, 高)） ----------
RESOLUTION_SIZE = {
    camera.FRAME_QQVGA: (160, 120),
    camera.FRAME_QVGA: (320, 240),
    camera.FRAME_VGA: (640, 480),
    camera.FRAME_SVGA: (800, 600),
    camera.FRAME_XGA: (1024, 768),
    camera.FRAME_UXGA: (1600, 1200),
}
# 如果 HQVGA 存在，补充尺寸
if hasattr(camera, "FRAME_HQVGA"):
    RESOLUTION_SIZE[camera.FRAME_HQVGA] = (240, 160)


# ---------- 4. 工具函数 ----------
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


# ---------- 5. 如果直接运行，打印列表 ----------
if __name__ == "__main__":
    list_resolutions()