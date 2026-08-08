# photo/brightness_analyzer.py
"""
灰度图像亮度分析工具。
提供灰度图像分析和捕获并分析的功能。
"""
from camera_driver import get_camera, CameraController, capture_grayscale
from flash import get_flash
import camera  # type: ignore
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="BrightnessAnalyzer")


def analyze_grayscale(gray_data, width, height):
    """
    分析灰度图像数据，返回亮度统计字典。

    Args:
        gray_data (bytes): 灰度图像数据（每字节一个像素）。
        width (int): 图像宽度（像素）。
        height (int): 图像高度（像素）。

    Returns:
        dict or None: 包含以下键的字典：
            - average_brightness (float): 全局平均亮度 (0-255)
            - dynamic_range (int): 最大亮度与最小亮度之差
            - center_brightness (float): 中心区域平均亮度
            - min (int): 最小亮度值
            - max (int): 最大亮度值
        如果 gray_data 无效则返回 None。
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


def capture_and_analyze_brightness(camera_params, framesize=None, flash_off=True):
    """
    捕获一帧灰度图像并分析环境亮度。

    Args:
        camera_params (dict): 摄像头初始化参数字典（包含 framesize 等）。
        framesize (int, optional): 指定分辨率，若不提供则使用 camera_params 中的值。
        flash_off (bool): 是否强制关闭闪光灯（默认 True，关闭）。

    Returns:
        dict or None: 同 analyze_grayscale 返回的字典，若失败则返回 None。
    """
    _debug_log("capture_and_analyze_brightness called, flash_off={}".format(flash_off))
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
        return analyze_grayscale(gray_buf, w, h)
    except Exception as e:
        _debug_log("Analysis error: {}".format(e))
        return None
    finally:
        cam.deinit()
        _debug_log("Camera released after analysis")


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    print("亮度分析模块测试：")
    # 模拟参数（实际需连接硬件）
    sample_params = {"framesize": camera.FRAME_QVGA}
    result = capture_and_analyze_brightness(sample_params, flash_off=True)
    if result:
        print("分析结果:", result)
    else:
        print("分析失败（可能无硬件）")