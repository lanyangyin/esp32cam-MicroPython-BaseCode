# decision/black_photo.py
"""
黑照检测决策模块
根据分辨率常量判断 JPEG 数据大小是否低于正常照片的最小阈值。
"""
import camera
from config import debug_log, LEVEL_DEBUG

# 各分辨率下正常照片的最小大小（字节），基于实际测试总结
MIN_SIZE_MAP = {
    camera.FRAME_96X96:   807,
    camera.FRAME_QQVGA:   1002,
    camera.FRAME_QCIF:    1122,
    camera.FRAME_HQVGA:   1452,
    camera.FRAME_240X240: 1752,
    camera.FRAME_QVGA:    2165,
    camera.FRAME_CIF:     2998,
    camera.FRAME_HVGA:    5531,
    camera.FRAME_VGA:     7291,
    camera.FRAME_SVGA:    11092,
    camera.FRAME_XGA:     16155,
    camera.FRAME_HD:      18627,
    camera.FRAME_SXGA:    26227,
    camera.FRAME_UXGA:    39143,
    camera.FRAME_FHD:     41127,
    camera.FRAME_P_HD:    18634,
    camera.FRAME_P_3MP:   26547,
    camera.FRAME_QXGA:    62942,
}

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

    min_size = MIN_SIZE_MAP.get(framesize, None)
    if min_size is None:
        debug_log("未知分辨率常量 {}, 跳过黑照检测".format(framesize), level=LEVEL_DEBUG, module="BlackPhoto")
        return False

    size = len(jpeg_data)
    is_black = size == min_size
    debug_log("黑照检测: framesize={}, 大小={}, 阈值={}, 判定={}".format(
        framesize, size, min_size, "黑照" if is_black else "正常"), level=LEVEL_DEBUG, module="BlackPhoto")
    return is_black