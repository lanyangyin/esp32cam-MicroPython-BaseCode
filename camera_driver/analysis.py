# camera_driver/analysis.py
"""摄像头数据分析（原 camera_analysis.py）"""
import math
import camera  # type: ignore
from .capture import capture_grayscale, capture_image   # 改为相对导入
from .controller import CameraController                # 改为相对导入
from utils.brightness import analyze_brightness, quick_brightness_estimate  # 依赖 utils 是正常的
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Analyzer")

def analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2):
    _debug_log("Starting analysis with framesize={}, step={}".format(framesize, step))
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None
    _debug_log("Gray image size: {} bytes".format(len(gray_buf)))
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            w, h = 640, 480
        _debug_log("Inferred size: {}x{}".format(w, h))
    else:
        _debug_log("Resolution: {}x{}".format(w, h))
    result = analyze_brightness(gray_buf, w, h, step)
    if result:
        _debug_log("Analysis complete: avg={:.1f}, dynamic={}, center={:.1f}".format(
            result['average_brightness'], result['dynamic_range'], result['center_brightness']))
    return result

def quick_brightness_from_camera(framesize=camera.FRAME_XGA):
    _debug_log("Quick brightness estimation with framesize={}".format(framesize))
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None
    _debug_log("Gray image size: {} bytes".format(len(gray_buf)))
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            w, h = 640, 480
        _debug_log("Inferred size: {}x{}".format(w, h))
    else:
        _debug_log("Resolution: {}x{}".format(w, h))
    result = quick_brightness_estimate(gray_buf, w, h)
    if result is not None:
        _debug_log("Quick estimate: {:.1f}".format(result))
    return result

def quick_brightness_with_jpeg(framesize=camera.FRAME_XGA, quality=10):
    _debug_log("Quick brightness with JPEG, framesize={}, quality={}".format(framesize, quality))
    avg = quick_brightness_from_camera(framesize)
    if avg is None:
        _debug_log("Brightness estimation failed, still trying to capture JPEG")
    _debug_log("Capturing JPEG image...")
    jpeg_data = capture_image(
        framesize=framesize,
        quality=quality,
        format=camera.JPEG,
        flip=1,
        mirror=0,
        whitebalance=camera.WB_CLOUDY
    )
    if jpeg_data is None:
        _debug_log("JPEG capture failed")
        return avg, None
    _debug_log("JPEG image size: {} bytes".format(len(jpeg_data)))
    return avg, jpeg_data