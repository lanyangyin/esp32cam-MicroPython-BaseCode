# photo/analyzers.py
"""灰度图像分析工具（原 PhotoCapturer 的 _analyze_gray 和 capture_analysis）"""
from camera_driver import get_camera, CameraController, capture_grayscale
from flash import get_flash
import camera  # type: ignore
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Photo")

def analyze_gray(gray_data, width, height):
    """
    分析灰度图像数据，返回亮度统计字典。
    原 PhotoCapturer._analyze_gray 的纯函数版本。
    """
    if not gray_data:
        return None
    total = 0
    min_val = 255
    max_val = 0
    num_pixels = width * height
    center_x_start = width // 4
    center_x_end = width - center_x_start
    center_y_start = height // 4
    center_y_end = height - center_y_start
    center_sum = 0
    center_count = 0
    idx = 0
    for y in range(height):
        for x in range(width):
            val = gray_data[idx]
            total += val
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
            if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                center_sum += val
                center_count += 1
            idx += 1
    avg = total / num_pixels
    dynamic = max_val - min_val
    center_avg = center_sum / center_count if center_count else avg
    _debug_log("Analysis result: avg={:.1f}, dynamic={}, center={:.1f}".format(avg, dynamic, center_avg))
    return {
        "average_brightness": avg,
        "dynamic_range": dynamic,
        "center_brightness": center_avg,
        "min": min_val,
        "max": max_val,
    }

def capture_analysis(camera_params, framesize=None, flash_off=True):
    """
    捕获一帧灰度图像并分析环境亮度（闪光灯默认关闭）。
    camera_params: 摄像头参数字典（包含 framesize 等）
    """
    _debug_log("capture_analysis called, flash_off={}".format(flash_off))
    if flash_off:
        flash = get_flash()
        flash.off()
        _debug_log("Flash ensured OFF")

    params = camera_params.copy()
    if framesize is not None:
        params["framesize"] = framesize
    params["format"] = camera.GRAYSCALE

    cam = get_camera()
    if cam.initialized:
        _debug_log("Deinit camera for analysis")
        cam.deinit()
    try:
        _debug_log("Init camera for grayscale analysis")
        cam.init(**params)
        gray_buf = cam.capture()
        if gray_buf is None:
            _debug_log("Gray capture failed")
            return None
        w, h = CameraController.get_resolution(params.get("framesize", camera.FRAME_XGA))
        _debug_log("Got resolution: {}x{}".format(w, h))
        return analyze_gray(gray_buf, w, h)
    except Exception as e:
        _debug_log("Analysis error: {}".format(e))
        return None
    finally:
        cam.deinit()
        _debug_log("Camera released after analysis")