# utils/contrast.py
"""
图像对比度计算工具（纯算法）
提供 RMS 对比度（标准差）的计算函数。
"""
import math


def compute_rms_contrast(gray_data, width, height, step=2):
    """
    计算灰度图像的 RMS 对比度（即像素强度的标准差）。

    参数：
        gray_data (bytes): 灰度图像数据（每像素 1 字节，0~255）
        width (int): 图像宽度
        height (int): 图像高度
        step (int): 采样步长，步长 2 表示每隔一个像素采样

    返回：
        float: RMS 对比度（标准差），若数据无效返回 None
    """
    if not gray_data or width <= 0 or height <= 0:
        return None

    expected_size = width * height
    if len(gray_data) < expected_size:
        return None

    # 第一次遍历：计算平均值
    total = 0
    count = 0
    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            total += gray_data[idx]
            count += 1

    if count == 0:
        return None

    mean = total / count

    # 第二次遍历：计算差值的平方和
    sum_sq_diff = 0
    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            val = gray_data[idx]
            diff = val - mean
            sum_sq_diff += diff * diff

    rms = math.sqrt(sum_sq_diff / count)
    return rms


def compute_rms_contrast_and_mean(gray_data, width, height, step=2):
    """
    同时计算 RMS 对比度和平均亮度，减少重复遍历。

    返回：
        tuple: (mean, rms_contrast)，若失败返回 (None, None)
    """
    if not gray_data or width <= 0 or height <= 0:
        return None, None

    expected_size = width * height
    if len(gray_data) < expected_size:
        return None, None

    total = 0
    count = 0
    # 收集数据以便第二次遍历（或使用列表存储采样值）
    # 为了减少内存开销，我们仍进行两次遍历，但合并为一次遍历并存储采样值
    # 对于小分辨率，直接存储采样值更高效
    samples = []
    for y in range(0, height, step):
        row_start = y * width
        for x in range(0, width, step):
            idx = row_start + x
            if idx >= len(gray_data):
                break
            val = gray_data[idx]
            samples.append(val)
            total += val
            count += 1

    if count == 0:
        return None, None

    mean = total / count

    sum_sq_diff = 0
    for val in samples:
        diff = val - mean
        sum_sq_diff += diff * diff

    rms = math.sqrt(sum_sq_diff / count)
    return mean, rms


if __name__ == "__main__":
    # 创建模拟数据
    import array
    w, h = 10, 10
    data = bytearray(w * h)
    # 填充梯度数据
    for i in range(w * h):
        data[i] = int((i / (w * h)) * 200 + 20)
    print("RMS 对比度:", compute_rms_contrast(data, w, h, step=1))