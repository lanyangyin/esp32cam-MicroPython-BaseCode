"""
camera_analyzer.py - 环境光亮度分析模块

本模块提供从摄像头捕获灰度图像并分析环境亮度的功能。

包含两种分析方式：
    1. analyze_brightness_from_camera() - 精确分析（支持采样步长）
    2. quick_brightness_from_camera() - 快速估计（仅 9 个点）

设计原则：
    - 本模块不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯）
    - 内部调用 camera_controller.capture_grayscale() 获取灰度图
    - 调用 utils 中的纯分析函数执行数据分析
    - 分析完成后自动释放摄像头资源

依赖关系：
    - camera_controller: 提供 capture_grayscale() 和分辨率查询
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
"""
import camera  # type: ignore
from camera_controller import capture_grayscale, CameraController
from utils import analyze_brightness, quick_brightness_estimate
from config import DEBUG

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

    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        import math
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

    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        import math
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


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    from camera_controller import reset_camera
    from utils import (
        create_gradient_image, create_checkerboard_image,
        create_center_bright_image, create_center_dark_image,
        analyze_brightness, quick_brightness_estimate,
        load_image_from_file, get_image_info
    )

    print("\n" + "="*50)
    print("  camera_analyzer 模块测试")
    print("="*50)

    # ========== 1. 模拟图片测试（无需摄像头） ==========
    print("\n--- 1. 模拟图片测试（无硬件依赖） ---")
    test_width, test_height = 320, 240

    test_scenarios = [
        ("水平渐变图", create_gradient_image(test_width, test_height, 'horizontal')),
        ("垂直渐变图", create_gradient_image(test_width, test_height, 'vertical')),
        ("棋盘格", create_checkerboard_image(test_width, test_height, 20)),
        ("中心亮（聚光效果）", create_center_bright_image(test_width, test_height, 0.25, 220, 30)),
        ("中心暗（逆光效果）", create_center_dark_image(test_width, test_height, 0.25, 30, 220)),
    ]

    for name, img_data in test_scenarios:
        print("\n  [{}]".format(name))
        # 精确分析
        result = analyze_brightness(img_data, test_width, test_height, step=2)
        if result:
            print(f"    精确分析: avg={result['average_brightness']:.1f}, "
                  f"dynamic={result['dynamic_range']}, center={result['center_brightness']:.1f}")
        # 快速估计
        quick = quick_brightness_estimate(img_data, test_width, test_height)
        if quick is not None:
            print(f"    快速估计: {quick:.1f}")

    # ========== 2. 从 SD 卡加载图片测试 ==========
    print("\n--- 2. SD 卡图片加载测试 ---")
    try:
        import uos
        files = uos.listdir('/sd')
        jpg_files = [f for f in files if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
        if jpg_files:
            test_file = '/sd/' + jpg_files[0]
            print("  加载文件: {}".format(test_file))
            img_data = load_image_from_file(test_file)
            if img_data:
                info = get_image_info(img_data)
                print("  文件信息: 格式={}, 大小={} bytes, 尺寸={}x{}".format(
                    info['format'], info['size_bytes'], info['width'], info['height']))
                # 注意：JPEG 是压缩数据，不能直接用于亮度分析
                # 这里仅演示文件加载成功
            else:
                print("  ❌ 加载失败")
        else:
            print("  ⚠️ 未找到 JPEG 文件，跳过")
    except Exception as e:
        print("  ⚠️ SD 卡读取失败: {}".format(e))

    # ========== 3. 真实摄像头测试（可选） ==========
    print("\n--- 3. 真实摄像头测试（需要硬件） ---")
    try:
        reset_camera()
        time.sleep_ms(200)

        # 测试精确分析（使用 QVGA 加速）
        print("  精确分析 (QVGA, step=2):")
        start = time.ticks_ms()
        result = analyze_brightness_from_camera(
            framesize=camera.FRAME_QVGA,
            step=2
        )
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        if result:
            print("    ✅ 成功: avg={:.1f}, dynamic={}, center={:.1f}, 耗时={} ms".format(
                result['average_brightness'], result['dynamic_range'],
                result['center_brightness'], elapsed))
        else:
            print("    ❌ 分析失败")

        # 测试快速估计
        print("  快速估计 (QVGA):")
        start = time.ticks_ms()
        avg = quick_brightness_from_camera(framesize=camera.FRAME_QVGA)
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        if avg is not None:
            print("    ✅ 成功: 亮度={:.1f}, 耗时={} ms".format(avg, elapsed))
        else:
            print("    ❌ 估计失败")

    except Exception as e:
        print("  ⚠️ 摄像头测试失败（可能无硬件）: {}".format(e))
        print("  提示: 前两项测试无需摄像头，已正常完成。")

    print("\n" + "="*50)
    print("  测试完成")
    print("="*50)

    # 速度对比（实测参考）
    # 精确分析（QVGA, step=2）约 0.3~0.5 秒，快速估计约 0.3~0.5 秒（主要耗时在图像捕获）
    # 但快速估计的分析计算只需几微秒，所以总耗时差异不大，但在高分辨率下快速估计优势明显

    # 📌 速度对比（实测参考）
    # 方案	分辨率	步长	约耗时
    # 原版	XGA	1	2~3秒
    # 原版	VGA	1	0.8~1秒
    # 原版	QVGA	1	0.3秒
    # 优化版	XGA	2	0.6~0.8秒
    # 建议：日常使用选择 VGA 或 QVGA，若必须高分辨率则用 step=2 或 3。