# photo/gray_analyzer.py
"""
标准灰度捕获与完整亮度分析模块（无闪光灯）

本模块提供完整的灰度图像捕获和亮度统计分析，
返回平均亮度、RMS 对比度、中心亮度、动态范围等信息。
适合需要详细场景亮度数据的场景。

特点：
    - 不控制闪光灯
    - 捕获后自动释放摄像头
    - 返回完整的亮度字典（avg, rms_contrast, center, dynamic 等）

典型用法：
    from photo import gray_analyzer_capture
    info = gray_analyzer_capture(framesize=camera.FRAME_VGA)
    if info:
        print("平均亮度:", info['average_brightness'])
        print("RMS 对比度:", info['rms_contrast'])
"""
import camera
from camera_driver import capture_grayscale, reset_camera, CameraController
from utils.brightness import analyze_brightness
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR


def gray_analyzer_capture(framesize=camera.FRAME_VGA, whitebalance=camera.WB_CLOUDY,
                          flip=1, mirror=0, step=2):
    """
    捕获一帧灰度图像，返回完整的亮度分析字典。

    参数：
        framesize (int): 分辨率常量，默认 FRAME_VGA。
        whitebalance (int): 白平衡模式，默认 WB_CLOUDY。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。
        step (int): 采样步长，默认 2。

    返回：
        dict or None: 包含 'average_brightness', 'rms_contrast', 'center_brightness',
                      'dynamic_range', 'min', 'max' 的字典，若失败返回 None。
    """
    debug_log("标准灰度捕获: framesize={}".format(framesize), level=LEVEL_INFO, module="GrayAnalyzer")

    # reset_camera()
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=whitebalance,
                                 flip=flip, mirror=mirror)
    if gray_buf is None:
        debug_log("灰度捕获失败", level=LEVEL_ERROR, module="GrayAnalyzer")
        return None

    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray_buf)
        w = int((total * 4 / 3) ** 0.5)
        h = total // w
        if w * h != total:
            w, h = 640, 480
        debug_log("分辨率推断: {}×{}".format(w, h), level=LEVEL_WARNING, module="GrayAnalyzer")

    result = analyze_brightness(gray_buf, w, h, step=step)
    if result is None:
        debug_log("亮度分析失败", level=LEVEL_WARNING, module="GrayAnalyzer")
        return None

    debug_log("分析结果: avg={:.1f}, rms={:.1f}, center={:.1f}".format(
        result['average_brightness'], result['rms_contrast'], result['center_brightness']),
        level=LEVEL_INFO, module="GrayAnalyzer")
    return result


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    for _ in range(20):
        print("标准灰度捕获测试（需硬件）")
        info = gray_analyzer_capture(framesize=camera.FRAME_VGA)
        if info:
            print("分析结果:")
            for k, v in info.items():
                print("  {}: {}".format(k, v))
        else:
            print("测试失败")