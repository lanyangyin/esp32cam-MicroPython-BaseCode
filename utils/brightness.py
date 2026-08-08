# utils/brightness.py
"""
亮度分析工具

提供灰度图像的亮度统计分析函数。
所有函数均为纯算法，无硬件依赖。
"""
from .contrast import compute_rms_contrast_and_mean


def analyze_brightness(gray_data, width, height, step=2):
    """
    分析灰度图像数据，计算平均亮度、RMS 对比度和中心区域亮度。

    返回字典包含：
        average_brightness (float): 整图平均灰度
        dynamic_range (int): 最大灰度 - 最小灰度（极差，向后兼容）
        rms_contrast (float): RMS 对比度（标准差）
        center_brightness (float): 中心区域平均灰度
        min (int): 最小灰度
        max (int): 最大灰度
    """
    if not gray_data or width <= 0 or height <= 0:
        return None

    expected_size = width * height
    if len(gray_data) < expected_size:
        return None

    # 计算平均值和 RMS 对比度
    mean, rms = compute_rms_contrast_and_mean(gray_data, width, height, step)
    if mean is None:
        return None

    # 计算中心区域亮度
    center_x_start = width // 4
    center_x_end = width - center_x_start
    center_y_start = height // 4
    center_y_end = height - center_y_start
    center_sum = 0
    center_count = 0

    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            if center_x_start <= x < center_x_end and center_y_start <= y < center_y_end:
                center_sum += gray_data[idx]
                center_count += 1

    center_avg = center_sum / center_count if center_count else mean

    # 计算极值（用于 dynamic_range）
    min_val = 255
    max_val = 0
    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            val = gray_data[idx]
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val

    return {
        'average_brightness': mean,
        'dynamic_range': max_val - min_val,   # 原有字段，保持兼容
        'rms_contrast': rms,                 # 新字段，更科学
        'center_brightness': center_avg,
        'min': min_val,
        'max': max_val,
    }

def quick_brightness_estimate(gray_data, width, height):
    """
    快速亮度估计：将图像分成 3×3 网格，取每个网格中心像素的灰度值，返回平均值。

    参数：
        gray_data (bytes): 灰度图像数据。
        width (int): 图像宽度。
        height (int): 图像高度。

    返回：
        float: 9 个网格中心点的平均亮度（0~255），若数据无效返回 None。
    """
    if not gray_data or width < 3 or height < 3:
        return None

    # 关键修复：校验数据长度
    expected_size = width * height
    if len(gray_data) < expected_size:
        return None

    total = 0
    step_x = width / 3.0
    step_y = height / 3.0

    for i in range(3):
        for j in range(3):
            x = int((j + 0.5) * step_x)
            y = int((i + 0.5) * step_y)
            if x >= width:
                x = width - 1
            if y >= height:
                y = height - 1
            idx = y * width + x
            total += gray_data[idx]

    return total / 9.0