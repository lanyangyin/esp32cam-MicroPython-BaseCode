# camera_analyzer.py
import camera
from camera_controller import CameraController
from flash import Flash


def analyze_brightness_from_camera(framesize=camera.FRAME_XGA,
                                   flash_off=True,
                                   flash_pin=4,
                                   flash_on_value=1):
    """
    捕获一帧灰度图，分析环境亮度、动态范围、主体亮度。
    参数：
        framesize      : 分辨率（默认 XGA 1024x768）
        flash_off      : 是否强制关闭闪光灯（True 表示分析环境光）
        flash_pin      : 闪光灯 GPIO 引脚
        flash_on_value : 闪光灯点亮电平（1 或 0）
    返回：
        字典 {
            'average_brightness' : float,   # 0~255 平均灰度
            'dynamic_range'      : int,     # 最大-最小
            'center_brightness'  : float    # 中央区域平均灰度
        }
        若失败返回 None。
    """
    # 1. 强制关闭闪光灯（避免影响环境光分析）
    if flash_off:
        flash = Flash(pin=flash_pin, on_value=flash_on_value)
        flash.off()

    # 2. 初始化灰度摄像头
    cam = CameraController()
    try:
        cam.init(
            framesize=framesize,
            format=camera.GRAYSCALE,  # 灰度模式，节省内存
            quality=10,  # 不影响灰度质量
            flip=1,  # 可根据需要调整
            mirror=0,
            whitebalance=camera.WB_CLOUDY,
        )
    except Exception as e:
        print("Camera init failed for analysis:", e)
        return None

    # 3. 捕获灰度图
    gray_buf = cam.capture()
    if gray_buf is None:
        print("Gray capture failed")
        cam.deinit()
        return None

    # 4. 获取图像尺寸
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        # 若无法映射，尝试从帧缓冲区推断（不精确）
        import math
        # 保守估算：假设宽高比 4:3
        total = len(gray_buf)
        w = int(math.sqrt(total * 4 / 3))
        h = total // w
        if w * h != total:
            # 若不能整除，回退
            w, h = 640, 480

    # 5. 分析灰度数据
    total = 0
    min_val = 255
    max_val = 0
    num_pixels = w * h

    # 中央区域（取画面中心 1/4）
    center_x_start = w // 4
    center_x_end = w - center_x_start
    center_y_start = h // 4
    center_y_end = h - center_y_start
    center_sum = 0
    center_count = 0

    idx = 0
    for y in range(h):
        for x in range(w):
            val = gray_buf[idx]
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

    cam.deinit()
    return {
        'average_brightness': avg,
        'dynamic_range': dynamic,
        'center_brightness': center_avg,
    }