"""
utils.py - 通用工具函数库

本模块提供与摄像头无关的通用工具函数，可被其他模块复用。

当前功能：
    - analyze_brightness(): 精确分析灰度图像数据的亮度统计（支持采样步长）
    - quick_brightness_estimate(): 快速亮度估计（3×3 网格中心采样，仅 9 个点）

设计原则：
    - 纯函数，无副作用
    - 不依赖硬件（摄像头、GPIO 等）
    - 可独立测试和复用
    - 工具函数不输出日志，日志由调用方控制

依赖关系：
    - 无外部依赖（仅使用标准 Python 语言特性）

典型用法：
    from utils import analyze_brightness, quick_brightness_estimate

    # 精确分析（可控制精度/速度）
    result = analyze_brightness(gray_data, width, height, step=2)

    # 快速估计（仅 9 个点，适用于简单场景）
    avg = quick_brightness_estimate(gray_data, width, height)
"""
# utils.py
# 通用工具函数库

def analyze_brightness(gray_data, width, height, step=2):
    """
    分析灰度图像数据，计算平均亮度、动态范围和中心区域亮度。

    本函数通过采样（步长可调）快速统计图像亮度分布。
    采样步长越大速度越快，但精度略降，推荐 2~4。

    参数：
        gray_data (bytes): 灰度图像数据（每字节一个像素，0~255）。
        width (int): 图像宽度。
        height (int): 图像高度。
        step (int): 采样步长，步长 2 表示每隔一个像素采样，速度提升约 4 倍。

    返回：
        dict: {
            'average_brightness': float,   # 整图平均灰度
            'dynamic_range': int,          # 最大灰度 - 最小灰度
            'center_brightness': float,    # 中央 1/4 区域平均灰度
        }
        若数据无效返回 None。
    """
    if not gray_data or width <= 0 or height <= 0:
        return None

    total = 0
    min_val = 255
    max_val = 0
    count = 0

    # 中央区域边界（画面中心 1/4）
    center_x_start = width // 4
    center_x_end = width - center_x_start
    center_y_start = height // 4
    center_y_end = height - center_y_start
    center_sum = 0
    center_count = 0

    # 使用步长采样
    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            val = gray_data[idx]
            total += val
            count += 1
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
            if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                center_sum += val
                center_count += 1

    if count == 0:
        return None

    avg = total / count
    dynamic = max_val - min_val
    center_avg = center_sum / center_count if center_count else avg

    return {
        'average_brightness': avg,
        'dynamic_range': dynamic,
        'center_brightness': center_avg,
    }


def quick_brightness_estimate(gray_data, width, height):
    """
    快速亮度估计：将图像分成 3×3 网格，取每个网格中心像素的灰度值，返回平均值。

    本函数仅读取 9 个像素，速度极快（微秒级），适用于需要快速了解环境光强弱的场景。
    若图像尺寸小于 3，则无法进行网格划分，返回 None。

    参数：
        gray_data (bytes): 灰度图像数据。
        width (int): 图像宽度。
        height (int): 图像高度。

    返回：
        float: 9 个网格中心点的平均亮度（0~255），若数据无效或尺寸不足则返回 None。
    """
    if not gray_data or width < 3 or height < 3:
        return None

    total = 0
    # 每个格子的步长（宽度/3，高度/3）
    step_x = width / 3.0
    step_y = height / 3.0

    for i in range(3):      # 行索引
        for j in range(3):  # 列索引
            # 计算当前格子中心点的坐标（使用 +0.5 偏移取中心）
            x = int((j + 0.5) * step_x)
            y = int((i + 0.5) * step_y)
            # 边界保护（防止浮点误差导致越界）
            if x >= width:
                x = width - 1
            if y >= height:
                y = height - 1
            idx = y * width + x
            total += gray_data[idx]

    return total / 9.0


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time

    print("\n--- utils 工具测试 ---")

    # 生成模拟灰度数据（渐变灰度）
    test_width = 320
    test_height = 240
    test_data = bytearray(test_width * test_height)
    for i in range(len(test_data)):
        test_data[i] = int((i / len(test_data)) * 200 + 20)

    # 测试精确分析
    print("1. 精确分析 (analyze_brightness, step=2):")
    start = time.ticks_ms()
    result = analyze_brightness(test_data, test_width, test_height, step=2)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if result:
        print(f"  平均亮度: {result['average_brightness']:.1f}")
        print(f"  动态范围: {result['dynamic_range']}")
        print(f"  中心亮度: {result['center_brightness']:.1f}")
        print(f"  耗时: {elapsed} ms")
    else:
        print("  分析失败")

    # 测试快速估计
    print("\n2. 快速估计 (quick_brightness_estimate):")
    start = time.ticks_ms()
    avg = quick_brightness_estimate(test_data, test_width, test_height)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if avg is not None:
        print(f"  估计平均亮度: {avg:.1f}")
        print(f"  耗时: {elapsed} ms")
    else:
        print("  估计失败")