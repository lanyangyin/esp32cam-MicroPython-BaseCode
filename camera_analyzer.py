"""
camera_analyzer.py - 环境光亮度分析模块

本模块提供从摄像头捕获灰度图像并分析环境亮度的功能。
核心函数 analyze_brightness_from_camera() 封装了完整的流程：
    捕获灰度图 -> 获取分辨率 -> 调用纯分析函数 -> 返回亮度数据

设计原则：
    - 本模块不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯）
    - 内部调用 camera_controller.capture_grayscale() 获取灰度图
    - 调用 utils.analyze_brightness() 执行纯数据分析
    - 分析完成后自动释放摄像头资源

依赖关系：
    - camera_controller: 提供 capture_grayscale() 和分辨率查询
    - utils: 提供 analyze_brightness() 纯分析函数
    - config: 调试开关

典型用法：
    result = analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2)
    if result:
        print(f"平均亮度: {result['average_brightness']:.1f}")
"""
# camera_analyzer.py
import camera  # type: ignore
from camera_controller import capture_grayscale, CameraController
from utils import analyze_brightness
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[Analyzer] " + msg)

def analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2):
    """
    捕获一帧灰度图像，分析环境亮度、动态范围和主体亮度。

    本函数不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯以测量环境光）。

    参数：
        framesize (int): 图像分辨率，如 camera.FRAME_XGA, FRAME_VGA 等。
        step (int): 采样步长，步长 2 表示每隔一个像素采样，速度提升约 4 倍。

    返回：
        dict: 包含 'average_brightness', 'dynamic_range', 'center_brightness'，
              若失败则返回 None。
    """
    _debug_log("Starting analysis with framesize={}, step={}".format(framesize, step))

    # 捕获灰度图像
    gray_buf = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray_buf is None:
        _debug_log("Failed to capture grayscale image")
        return None

    # 获取图像尺寸
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        # 从缓冲区推断
        import math
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            w, h = 640, 480  # 安全回退
        _debug_log("Inferred size: {}x{}".format(w, h))
    else:
        _debug_log("Resolution: {}x{}".format(w, h))

    # 调用纯分析函数
    result = analyze_brightness(gray_buf, w, h, step)
    if result:
        _debug_log("Analysis complete: avg={:.1f}, dynamic={}, center={:.1f}".format(
            result['average_brightness'], result['dynamic_range'], result['center_brightness']))
    return result

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    from camera_controller import reset_camera

    print("\n--- camera_analyzer 模块测试 ---")
    reset_camera()
    time.sleep_ms(200)

    start = time.ticks_ms()
    result = analyze_brightness_from_camera(
        framesize=camera.FRAME_QVGA,
        step=2
    )
    if result:
        print("✅ 分析成功:")
        print(f"  平均亮度: {result['average_brightness']:.1f}")
        print(f"  动态范围: {result['dynamic_range']}")
        print(f"  中心亮度: {result['center_brightness']:.1f}")
    else:
        print("❌ 分析失败")
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))

    # 📌 速度对比（实测参考）
    # 方案	分辨率	步长	约耗时
    # 原版	XGA	1	2~3秒
    # 原版	VGA	1	0.8~1秒
    # 原版	QVGA	1	0.3秒
    # 优化版	XGA	2	0.6~0.8秒
    # 建议：日常使用选择 VGA 或 QVGA，若必须高分辨率则用 step=2 或 3。