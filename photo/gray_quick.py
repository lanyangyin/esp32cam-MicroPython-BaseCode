# photo/gray_quick.py
"""
快速灰度捕获与亮度估计模块（无闪光灯）

本模块提供独立于闪光灯的灰度图像捕获功能，
仅获取 3×3 网格中心 9 个像素的平均亮度估计值。
适合需要快速判断环境光线强度的场景。

特点：
    - 不控制闪光灯（调用者自行管理）
    - 不进行重拍或重试（直接返回结果）
    - 捕获后自动释放摄像头
    - 纯函数，无副作用

典型用法：
    from photo import gray_quick_capture
    avg = gray_quick_capture(framesize=camera.FRAME_QVGA)
    if avg is not None:
        print("快速亮度估计:", avg)
"""
import camera
from camera_driver import capture_grayscale, reset_camera, CameraController
from utils.brightness import quick_brightness_estimate
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR


def gray_quick_capture(framesize=camera.FRAME_QVGA, whitebalance=camera.WB_CLOUDY,
                       flip=1, mirror=0):
    """
    捕获一帧灰度图像，返回 3×3 网格中心 9 个像素的平均亮度估计值。

    参数：
        framesize (int): 分辨率常量，默认 FRAME_QVGA（速度快）。
        whitebalance (int): 白平衡模式，默认 WB_CLOUDY。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。

    返回：
        float or None: 9 个中心点的平均亮度（0~255），若失败返回 None。
    """
    debug_log("快速灰度捕获: framesize={}".format(framesize), level=LEVEL_INFO, module="GrayQuick")

    # reset_camera()  # 确保摄像头干净状态
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=whitebalance,
                                 flip=flip, mirror=mirror)
    if gray_buf is None:
        debug_log("灰度捕获失败", level=LEVEL_ERROR, module="GrayQuick")
        return None

    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        # 尝试推断尺寸（通常灰度图大小为 w*h）
        total = len(gray_buf)
        w = int((total * 4 / 3) ** 0.5)
        h = total // w
        if w * h != total:
            w, h = 320, 240
        debug_log("分辨率推断: {}×{}".format(w, h), level=LEVEL_WARNING, module="GrayQuick")

    avg = quick_brightness_estimate(gray_buf, w, h)
    if avg is None:
        debug_log("亮度估计失败", level=LEVEL_WARNING, module="GrayQuick")
        return None

    debug_log("快速亮度估计: {:.1f}".format(avg), level=LEVEL_INFO, module="GrayQuick")
    return avg


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    for _ in range(20):
        print("快速灰度捕获测试（需硬件）")
        avg = gray_quick_capture(framesize=camera.FRAME_QVGA)
        if avg is not None:
            print("亮度估计值: {:.1f}".format(avg))
        else:
            print("测试失败")