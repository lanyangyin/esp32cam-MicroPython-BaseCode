"""
camera_analyzer.py - 环境光亮度分析模块

本模块提供从摄像头捕获灰度图像并分析环境亮度的功能。

包含三种分析方式：
    1. analyze_brightness_from_camera() - 精确分析（支持采样步长），输出灰度图大小
    2. quick_brightness_from_camera() - 快速估计（仅 9 个点），输出灰度图大小
    3. quick_brightness_with_jpeg() - 快速估计 + 拍摄 JPEG 照片并输出大小

设计原则：
    - 本模块不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯）
    - 内部调用 camera_controller 中的捕获函数
    - 调用 utils 中的纯分析函数执行数据分析
    - 分析完成后自动释放摄像头资源
    - 所有捕获的图片大小均通过 DEBUG 日志输出

依赖关系：
    - camera_controller: 提供 capture_grayscale(), capture_image() 和分辨率查询
    - utils: 提供 analyze_brightness() 和 quick_brightness_estimate()
    - config: 调试开关

典型用法：
    # 精确分析
    result = analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2)
    if result:
        print(f"平均亮度: {result['average_brightness']:.1f}")

    # 快速估计
    avg = quick_brightness_from_camera(framesize=camera.FRAME_VGA)
    if avg is not None:
        print(f"快速亮度估计: {avg:.1f}")

    # 快速估计 + 拍照
    avg, jpeg_data = quick_brightness_with_jpeg(framesize=camera.FRAME_VGA, quality=15)
    if avg is not None:
        print(f"亮度: {avg:.1f}, JPEG 大小: {len(jpeg_data)} bytes")
"""
import math

import camera  # type: ignore

from camera_controller import capture_grayscale, capture_image, CameraController
from config import DEBUG
from utils import analyze_brightness, quick_brightness_estimate


def _debug_log(msg):
    if DEBUG:
        print("[Analyzer] " + msg)


def analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2):
    """
    捕获一帧灰度图像，精确分析环境亮度、动态范围和主体亮度。

    本函数不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯以测量环境光）。

    参数：
        framesize (int): 图像分辨率，如 camera.FRAME_XGA, FRAME_VGA 等。
        step (int): 采样步长，步长 2 表示每隔一个像素采样，速度提升约 4 倍。

    返回：
        dict: 包含 'average_brightness', 'dynamic_range', 'center_brightness'，
              若失败则返回 None。
    """
    _debug_log("Starting analysis with framesize={}, step={}".format(framesize, step))

    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None

    # 输出灰度图大小
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
    """
    快速亮度估计：捕获一帧灰度图像，使用 3×3 网格中心采样（仅 9 个点）估计环境亮度。

    本函数速度极快（约微秒级），适合快速判断环境光强弱，用于触发逻辑（如自动曝光决策）。
    不控制闪光灯，调用者需自行管理。

    参数：
        framesize (int): 图像分辨率，建议使用较低分辨率以进一步加快速度。

    返回：
        float: 9 个网格中心点的平均亮度（0~255），若失败返回 None。
    """
    _debug_log("Quick brightness estimation with framesize={}".format(framesize))

    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None

    # 输出灰度图大小
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
    """
    快速亮度估计 + 拍摄 JPEG 照片，并输出照片的字节大小。

    此函数先以灰度模式捕获一帧进行快速亮度估计（3×3 网格），
    再以 JPEG 模式捕获一张照片，返回亮度估计值和 JPEG 数据。

    不控制闪光灯，调用者需自行管理。

    参数：
        framesize (int): 图像分辨率，建议使用较低分辨率以加快速度。
        quality (int): JPEG 质量（10~63，数值越小画质越好文件越大），默认 10。

    返回：
        tuple: (avg, jpeg_data)
            - avg (float): 快速亮度估计值（0~255），若失败为 None。
            - jpeg_data (bytes): JPEG 图像数据，若失败为 None。
    """
    _debug_log("Quick brightness with JPEG, framesize={}, quality={}".format(framesize, quality))

    # 1. 快速亮度估计（灰度模式）
    avg = quick_brightness_from_camera(framesize)
    if avg is None:
        _debug_log("Brightness estimation failed, still trying to capture JPEG")

    # 2. 拍摄 JPEG 照片
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


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    from camera_controller import reset_camera

    print("\n--- camera_analyzer 模块测试 ---")
    reset_camera()
    time.sleep_ms(200)

    # 1. 精确分析
    print("\n1. 精确分析 (analyze_brightness_from_camera):")
    start = time.ticks_ms()
    result = analyze_brightness_from_camera(
        framesize=camera.FRAME_QVGA,
        step=2
    )
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if result:
        print("✅ 分析成功:")
        print(f"  平均亮度: {result['average_brightness']:.1f}")
        print(f"  动态范围: {result['dynamic_range']}")
        print(f"  中心亮度: {result['center_brightness']:.1f}")
        print(f"  耗时: {elapsed} ms")
    else:
        print("❌ 分析失败")

    # 2. 快速估计
    print("\n2. 快速估计 (quick_brightness_from_camera):")
    start = time.ticks_ms()
    avg = quick_brightness_from_camera(framesize=camera.FRAME_QVGA)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if avg is not None:
        print(f"✅ 估计成功: 亮度 = {avg:.1f} (耗时 {elapsed} ms)")
    else:
        print("❌ 估计失败")

    # 3. 快速估计 + 拍照
    print("\n3. 快速估计 + 拍照 (quick_brightness_with_jpeg):")
    start = time.ticks_ms()
    avg, jpeg_data = quick_brightness_with_jpeg(
        framesize=camera.FRAME_QVGA,
        quality=15
    )
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if avg is not None and jpeg_data is not None:
        print(f"✅ 成功: 亮度 = {avg:.1f}, JPEG 大小 = {len(jpeg_data)} bytes (耗时 {elapsed} ms)")
    elif avg is not None:
        print(f"⚠️ 亮度估计成功 ({avg:.1f})，但 JPEG 捕获失败")
    elif jpeg_data is not None:
        print(f"⚠️ JPEG 捕获成功 (大小 {len(jpeg_data)} bytes)，但亮度估计失败")
    else:
        print("❌ 两项都失败")

    # 速度对比（实测参考）
    print("\n📌 速度参考:")
    print("  精确分析（QVGA, step=2）约 0.3~0.5 秒")
    print("  快速估计（QVGA）约 0.3~0.5 秒（主要耗时在图像捕获）")
    print("  快速估计+拍照（QVGA）约 0.6~1.0 秒（两次捕获）")