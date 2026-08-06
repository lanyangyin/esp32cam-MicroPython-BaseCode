# camera_analyzer.py
import camera
from camera_controller import get_camera, CameraController
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[Analyzer] " + msg)

def analyze_brightness_from_camera(framesize=camera.FRAME_XGA, step=2):
    """
    捕获一帧灰度图像，分析环境亮度、动态范围和主体亮度。

    本函数不控制闪光灯，调用者需自行管理（通常分析前应关闭闪光灯以测量环境光）。
    使用单例摄像头，捕获后自动释放。

    参数：
        framesize (int): 图像分辨率，如 camera.FRAME_XGA, FRAME_VGA 等。
        step (int): 采样步长，步长 2 表示每隔一个像素采样，速度提升约 4 倍。

    返回：
        dict: 包含 'average_brightness' (float), 'dynamic_range' (int), 'center_brightness' (float)，
              若失败则返回 None。
    """
    _debug_log("Starting analysis with framesize={}, step={}".format(framesize, step))
    cam = get_camera()
    if cam.initialized:
        _debug_log("Deinitializing existing camera")
        cam.deinit()

    try:
        _debug_log("Initializing camera in grayscale mode")
        cam.init(
            framesize=framesize,
            format=camera.GRAYSCALE,
            quality=10,
            flip=1,
            mirror=0,
            whitebalance=camera.WB_CLOUDY,
        )
        _debug_log("Capturing grayscale image...")
        gray_buf = cam.capture()
        if gray_buf is None:
            _debug_log("Gray capture failed")
            return None

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            import math
            total = len(gray_buf)
            w = int(math.sqrt(total * 4 / 3))
            h = total // w
            if w * h != total:
                w, h = 640, 480
        _debug_log("Image size: {}x{}".format(w, h))

        # 快速采样分析
        total = 0
        min_val = 255
        max_val = 0
        count = 0

        center_x_start = w // 4
        center_x_end = w - center_x_start
        center_y_start = h // 4
        center_y_end = h - center_y_start
        center_sum = 0
        center_count = 0

        for y in range(0, h, step):
            row_start = y * w
            for x in range(0, w, step):
                idx = row_start + x
                if idx >= len(gray_buf):
                    break
                val = gray_buf[idx]
                total += val
                count += 1
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val
                if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                    center_sum += val
                    center_count += 1

        avg = total / count
        dynamic = max_val - min_val
        center_avg = center_sum / center_count if center_count else avg

        _debug_log("Analysis complete: avg={:.1f}, dynamic={}, center={:.1f}".format(avg, dynamic, center_avg))
        return {
            'average_brightness': avg,
            'dynamic_range': dynamic,
            'center_brightness': center_avg,
        }
    except Exception as e:
        _debug_log("Analysis error: {}".format(e))
        return None
    finally:
        cam.deinit()
        _debug_log("Camera released")

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    print("\n--- camera_analyzer 模块测试 ---")
    start = time.ticks_ms()

    # 测试分析（使用小分辨率）
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