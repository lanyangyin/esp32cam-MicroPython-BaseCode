# camera_analyzer.py
import camera
from camera_controller import CameraController
from flash import Flash


def analyze_brightness_from_camera(framesize=camera.FRAME_XGA,
                                   flash_off=True,
                                   flash_pin=4,
                                   flash_on_value=1,
                                   step=2):
    """
    捕获一帧灰度图像，分析环境亮度、动态范围和主体亮度。

    本函数独立于拍照流程，适用于快速场景评估（如自动曝光控制前预处理）。
    分析时默认关闭闪光灯以测量真实环境光。

    参数：
        framesize (int): 图像分辨率，如 camera.FRAME_XGA, FRAME_VGA 等。
                         建议使用较低分辨率（如 VGA）以加快速度。
        flash_off (bool): 是否强制关闭闪光灯。True 表示关闭，False 则保持当前状态。
        flash_pin (int): 闪光灯 GPIO 引脚，默认 4。
        flash_on_value (int): 闪光灯点亮电平，1 高电平点亮，0 低电平点亮。
        step (int): 采样步长。步长为 2 表示每隔一个像素采样，速度提升约 4 倍，
                    且对整体亮度估计影响很小。步长越大速度越快，但精度略降。

    返回：
        dict: 包含以下键值对，若失败则返回 None：
            - 'average_brightness' (float): 整张图像的平均灰度值，范围 0~255。
            - 'dynamic_range' (int): 最大灰度与最小灰度的差值，反映图像对比度。
            - 'center_brightness' (float): 画面中央 1/4 区域的平均灰度，用于估计主体亮度。
    """
    # 若需要关闭闪光灯，则实例化 Flash 并关闭
    if flash_off:
        flash = Flash(pin=flash_pin, on_value=flash_on_value)
        flash.off()

    cam = CameraController()
    try:
        # 初始化灰度摄像头
        cam.init(
            framesize=framesize,
            format=camera.GRAYSCALE,  # 灰度格式，节省内存
            quality=10,  # 对灰度无影响
            flip=1,
            mirror=0,
            whitebalance=camera.WB_CLOUDY,
        )
        # 捕获灰度图
        gray_buf = cam.capture()
        if gray_buf is None:
            print("Gray capture failed")
            return None

        # 获取图像尺寸
        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            # 若未映射，则从缓冲区长度估算（假设宽高比 4:3）
            import math
            total = len(gray_buf)
            w = int(math.sqrt(total * 4 / 3))
            h = total // w
            if w * h != total:
                w, h = 640, 480  # 安全回退

        # ---------- 快速采样分析 ----------
        total = 0
        min_val = 255
        max_val = 0
        count = 0

        # 中央区域边界（取画面中心 1/4）
        center_x_start = w // 4
        center_x_end = w - center_x_start
        center_y_start = h // 4
        center_y_end = h - center_y_start
        center_sum = 0
        center_count = 0

        # 使用步长遍历像素（跳过部分像素以提高速度）
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
                # 判断是否在中央区域
                if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                    center_sum += val
                    center_count += 1

        avg = total / count
        dynamic = max_val - min_val
        center_avg = center_sum / center_count if center_count else avg

        return {
            'average_brightness': avg,
            'dynamic_range': dynamic,
            'center_brightness': center_avg,
        }
    except Exception as e:
        print("Analysis error:", e)
        return None
    finally:
        cam.deinit()  # 确保释放摄像头资源