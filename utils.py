"""
utils.py - 通用工具函数库

本模块提供与摄像头无关的通用工具函数，可被其他模块复用。

当前功能：
    - analyze_brightness(): 分析灰度图像数据的亮度统计

设计原则：
    - 纯函数，无副作用
    - 不依赖硬件（摄像头、GPIO 等）
    - 可独立测试和复用

依赖关系：
    - 无外部依赖（仅使用标准 Python 语言特性）

典型用法：
    from utils import analyze_brightness

    result = analyze_brightness(gray_data, width, height, step=2)
    print(f"平均亮度: {result['average_brightness']:.1f}")
"""
# utils.py
# 通用工具函数库

def analyze_brightness(gray_data, width, height, step=2):
    """
    分析灰度图像数据，计算平均亮度、动态范围和中心区域亮度。

    本函数不涉及摄像头操作，仅对灰度数据进行统计分析，可作为独立工具使用。

    参数：
        gray_data (bytes): 灰度图像数据（每字节一个像素，0~255）。
        width (int): 图像宽度。
        height (int): 图像高度。
        step (int): 采样步长，步长 2 表示每隔一个像素采样，速度提升约 4 倍。
                   步长越大速度越快，但精度略降，推荐 2~4。

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


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time

    print("\n--- utils.analyze_brightness 工具测试 ---")
    # 生成模拟灰度数据（渐变灰度）
    test_width = 320
    test_height = 240
    test_data = bytearray(test_width * test_height)
    for i in range(len(test_data)):
        test_data[i] = int((i / len(test_data)) * 200 + 20)  # 模拟从暗到亮
    start = time.ticks_ms()
    result = analyze_brightness(test_data, test_width, test_height, step=2)
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    if result:
        print("✅ 分析成功:")
        print(f"  平均亮度: {result['average_brightness']:.1f}")
        print(f"  动态范围: {result['dynamic_range']}")
        print(f"  中心亮度: {result['center_brightness']:.1f}")
        print(f"耗时: {elapsed} ms")
    else:
        print("❌ 分析失败")