# decision/black_photo.py
"""
黑照检测决策模块
根据分辨率常量判断 JPEG 数据大小是否低于正常照片的最小阈值。
支持按摄像头型号加载不同的阈值配置。
"""
import camera
import json
from config import debug_log, LEVEL_DEBUG, LEVEL_WARNING
from config.camera_model import get_config_path, get_camera_model

# 内置默认阈值（适用于 OV3660，作为回退）
DEFAULT_MIN_SIZE_MAP = {
    "FRAME_96X96":   807,
    "FRAME_QQVGA":   1002,
    "FRAME_QCIF":    1122,
    "FRAME_HQVGA":   1452,
    "FRAME_240X240": 1752,
    "FRAME_QVGA":    2165,
    "FRAME_CIF":     2998,
    "FRAME_HVGA":    5531,
    "FRAME_VGA":     7291,
    "FRAME_SVGA":    11092,
    "FRAME_XGA":     16155,
    "FRAME_HD":      18627,
    "FRAME_SXGA":    26227,
    "FRAME_UXGA":    39143,
    "FRAME_FHD":     41127,
    "FRAME_P_HD":    18634,
    "FRAME_P_3MP":   26547,
    "FRAME_QXGA":    62942,
}

_cached_min_size_map = None

def _load_min_size_map():
    """加载当前型号的黑照阈值配置，若失败则使用内置默认值"""
    global _cached_min_size_map
    if _cached_min_size_map is not None:
        return _cached_min_size_map

    # 尝试从型号配置目录加载 black_photo_config.json
    try:
        path = get_config_path("black_photo_config.json")
        with open(path, 'r') as f:
            data = json.load(f)
        # 将字符串键转为 int 常量（通过 camera 模块）
        min_map = {}
        for name, value in data.items():
            if name.startswith('_'):
                continue  # 跳过注释字段
            if hasattr(camera, name):
                const = getattr(camera, name)
                min_map[const] = value
            else:
                debug_log("忽略未知分辨率名称: {}".format(name), level=LEVEL_WARNING, module="BlackPhoto")
        _cached_min_size_map = min_map
        debug_log("加载黑照阈值配置: {} 项".format(len(min_map)), level=LEVEL_DEBUG, module="BlackPhoto")
        return _cached_min_size_map
    except Exception as e:
        debug_log("加载黑照配置失败 ({}), 使用内置默认值".format(e), level=LEVEL_WARNING, module="BlackPhoto")
        # 将默认值转换为常量键
        default_map = {}
        for name, value in DEFAULT_MIN_SIZE_MAP.items():
            if hasattr(camera, name):
                default_map[getattr(camera, name)] = value
        _cached_min_size_map = default_map
        return _cached_min_size_map


def is_black_photo(jpeg_data, framesize):
    """
    判断 JPEG 照片是否为“黑照”（无效照片）。
    基于照片大小与对应分辨率的最小阈值比较。

    参数：
        jpeg_data (bytes): JPEG 图像数据
        framesize (int): 摄像头分辨率常量

    返回：
        bool: True 表示可能是黑照（应重试），False 表示照片可用。
    """
    if not jpeg_data:
        return True

    min_size_map = _load_min_size_map()
    min_size = min_size_map.get(framesize, None)
    if min_size is None:
        debug_log("未知分辨率常量 {}, 跳过黑照检测".format(framesize), level=LEVEL_DEBUG, module="BlackPhoto")
        return False

    size = len(jpeg_data)
    is_black = size == min_size
    debug_log("黑照检测: framesize={}, 大小={}, 阈值={}, 判定={}".format(
        framesize, size, min_size, "黑照" if is_black else "正常"), level=LEVEL_DEBUG, module="BlackPhoto")
    return is_black