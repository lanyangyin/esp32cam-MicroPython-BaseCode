"""
utils.py - 通用工具函数库

本模块提供与摄像头无关的通用工具函数，可被其他模块复用。

当前功能：
    - analyze_brightness(): 精确分析灰度图像数据的亮度统计（支持采样步长）
    - quick_brightness_estimate(): 快速亮度估计（3×3 网格中心采样，仅 9 个点）
    - get_image_info(): 获取图片的详细元信息（大小、格式、尺寸等）
    - get_image_size(): 获取图片文件大小（字节）
    - get_image_dimensions(): 获取图片尺寸（宽×高）

设计原则：
    - 纯函数，无副作用
    - 不依赖硬件（摄像头、GPIO 等）
    - 可独立测试和复用
    - 工具函数不输出日志，日志由调用方控制

依赖关系：
    - 无外部依赖（仅使用标准 Python 语言特性）

典型用法：
    from utils import analyze_brightness, quick_brightness_estimate, get_image_info

    # 精确分析（可控制精度/速度）
    result = analyze_brightness(gray_data, width, height, step=2)

    # 快速估计（仅 9 个点，适用于简单场景）
    avg = quick_brightness_estimate(gray_data, width, height)

    # 获取图片信息
    info = get_image_info(image_data)
    print(f"大小: {info['size_bytes']} bytes, 格式: {info['format']}")
"""
import struct


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


# ========== 图片信息提取工具函数 ==========

def get_image_info(image_data):
    """
    获取图片的详细元信息。

    本函数支持 JPEG 和 PNG 格式的图片信息提取。

    参数：
        image_data (bytes): 图片的二进制数据。

    返回：
        dict: {
            'size_bytes': int,      # 文件大小（字节）
            'format': str,          # 图片格式（'JPEG', 'PNG', 'UNKNOWN'）
            'width': int,           # 图片宽度（像素），未知时为 0
            'height': int,          # 图片高度（像素），未知时为 0
            'is_jpeg': bool,        # 是否为 JPEG 格式
            'is_png': bool,         # 是否为 PNG 格式
        }
        若数据无效返回 None。
    """
    if not image_data or len(image_data) < 8:
        return None

    size_bytes = len(image_data)
    result = {
        'size_bytes': size_bytes,
        'format': 'UNKNOWN',
        'width': 0,
        'height': 0,
        'is_jpeg': False,
        'is_png': False,
    }

    # 检测 JPEG 格式（SOI 标记 0xFFD8）
    if image_data[0:2] == b'\xff\xd8':
        result['format'] = 'JPEG'
        result['is_jpeg'] = True
        # 尝试从 JPEG 中提取尺寸（解析 SOF 段）
        w, h = _parse_jpeg_dimensions(image_data)
        if w and h:
            result['width'] = w
            result['height'] = h

    # 检测 PNG 格式（文件头 0x89504E47）
    elif image_data[0:8] == b'\x89PNG\r\n\x1a\n':
        result['format'] = 'PNG'
        result['is_png'] = True
        # PNG 尺寸在 IHDR 块中（偏移 16 字节）
        if len(image_data) >= 24:
            w, h = struct.unpack('>II', image_data[16:24])
            result['width'] = w
            result['height'] = h

    return result


def get_image_size(image_data):
    """
    获取图片文件大小（字节）。

    参数：
        image_data (bytes): 图片的二进制数据。

    返回：
        int: 文件大小（字节），若数据无效返回 0。
    """
    if not image_data:
        return 0
    return len(image_data)


def get_image_dimensions(image_data):
    """
    获取图片尺寸（宽×高）。

    参数：
        image_data (bytes): 图片的二进制数据。

    返回：
        tuple: (width, height)，若无法解析返回 (0, 0)。
    """
    info = get_image_info(image_data)
    if info:
        return (info['width'], info['height'])
    return (0, 0)


# ========== 内部辅助函数 ==========

def _parse_jpeg_dimensions(jpeg_data):
    """
    从 JPEG 数据中解析图片尺寸（内部函数）。

    遍历 JPEG 段，查找 SOF0（0xFFC0）或 SOF2（0xFFC2）段获取尺寸。

    参数：
        jpeg_data (bytes): JPEG 图片数据。

    返回：
        tuple: (width, height)，若解析失败返回 (0, 0)。
    """
    idx = 2  # 跳过 SOI 标记
    data_len = len(jpeg_data)

    while idx < data_len - 1:
        # 查找标记（0xFF）
        if jpeg_data[idx] != 0xFF:
            idx += 1
            continue

        marker = jpeg_data[idx + 1]
        idx += 2

        # SOF0 (0xC0) 或 SOF2 (0xC2) - 包含尺寸信息
        if marker == 0xC0 or marker == 0xC2:
            if idx + 5 <= data_len:
                height = (jpeg_data[idx + 1] << 8) + jpeg_data[idx + 2]
                width = (jpeg_data[idx + 3] << 8) + jpeg_data[idx + 4]
                return (width, height)
            return (0, 0)

        # 跳过段数据（RST 标记 0xD0-0xD7 没有长度字段）
        if 0xD0 <= marker <= 0xD7:
            continue

        # 读取段长度
        if idx + 1 > data_len:
            return (0, 0)
        segment_len = (jpeg_data[idx] << 8) + jpeg_data[idx + 1]
        idx += segment_len

    return (0, 0)


# ========== 新增：生成测试图片的函数 ==========

def create_uniform_image(width, height, value=128):
    """
    生成均匀灰度图（所有像素值相同）。

    参数：
        width (int): 图像宽度。
        height (int): 图像高度。
        value (int): 灰度值（0~255），默认 128（中灰）。

    返回：
        bytes: 灰度图像数据（长度为 width * height）。
    """
    if width <= 0 or height <= 0 or not (0 <= value <= 255):
        return None
    return bytes([value]) * (width * height)


def create_gradient_image(width, height, direction='horizontal'):
    """
    生成渐变灰度图（从黑到白线性渐变）。

    参数：
        width (int): 图像宽度。
        height (int): 图像高度。
        direction (str): 'horizontal' 或 'vertical'，渐变方向。

    返回：
        bytes: 灰度图像数据。
    """
    if width <= 0 or height <= 0:
        return None
    data = bytearray(width * height)
    if direction == 'horizontal':
        for y in range(height):
            row_start = y * width
            for x in range(width):
                data[row_start + x] = int((x / width) * 255)
    elif direction == 'vertical':
        for y in range(height):
            row_start = y * width
            value = int((y / height) * 255)
            for x in range(width):
                data[row_start + x] = value
    else:
        return None
    return bytes(data)


def create_checkerboard_image(width, height, block_size=20):
    """
    生成棋盘格灰度图（黑白交替）。

    参数：
        width (int): 图像宽度。
        height (int): 图像高度。
        block_size (int): 每个棋盘格的大小（像素）。

    返回：
        bytes: 灰度图像数据。
    """
    if width <= 0 or height <= 0 or block_size <= 0:
        return None
    data = bytearray(width * height)
    for y in range(height):
        row_start = y * width
        for x in range(width):
            # 计算所在棋盘格的行列索引
            cell_x = x // block_size
            cell_y = y // block_size
            # 黑白交替
            value = 255 if (cell_x + cell_y) % 2 == 0 else 0
            data[row_start + x] = value
    return bytes(data)


def create_center_bright_image(width, height, center_radius_ratio=0.3,
                               center_value=200, surround_value=50):
    """
    生成中心亮、周围暗的灰度图（模拟聚光效果）。

    参数：
        width (int): 图像宽度。
        height (int): 图像高度。
        center_radius_ratio (float): 中心亮区半径占图像短边的比例（0~1）。
        center_value (int): 中心区域灰度值（0~255）。
        surround_value (int): 周围区域灰度值（0~255）。

    返回：
        bytes: 灰度图像数据。
    """
    if width <= 0 or height <= 0 or not (0 < center_radius_ratio <= 1):
        return None
    cx = width / 2
    cy = height / 2
    radius = min(width, height) * center_radius_ratio / 2
    radius_sq = radius * radius

    data = bytearray(width * height)
    for y in range(height):
        row_start = y * width
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist_sq = dx*dx + dy*dy
            if dist_sq <= radius_sq:
                data[row_start + x] = center_value
            else:
                data[row_start + x] = surround_value
    return bytes(data)


def create_center_dark_image(width, height, center_radius_ratio=0.3,
                             center_value=50, surround_value=200):
    """
    生成中心暗、周围亮的灰度图（模拟逆光或阴影效果）。

    参数：
        width (int): 图像宽度。
        height (int): 图像高度。
        center_radius_ratio (float): 中心暗区半径占图像短边的比例（0~1）。
        center_value (int): 中心区域灰度值（0~255）。
        surround_value (int): 周围区域灰度值（0~255）。

    返回：
        bytes: 灰度图像数据。
    """
    return create_center_bright_image(width, height, center_radius_ratio,
                                      center_value, surround_value)


def load_image_from_file(filepath):
    """
    从文件加载图片数据，返回字节对象。

    参数：
        filepath (str): 图片文件路径（支持 JPEG、PNG 等）。

    返回：
        bytes: 图片的二进制数据，若失败返回 None。
    """
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except Exception as e:
        print("[utils] Failed to load image from {}: {}".format(filepath, e))
        return None


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    import gc

    print("\n--- utils 工具测试 ---")

    # 生成模拟灰度数据（渐变灰度）
    test_width = 320
    test_height = 240
    test_data = bytearray(test_width * test_height)
    for i in range(len(test_data)):
        test_data[i] = int((i / len(test_data)) * 200 + 20)

    print("1. 原有函数测试 (analyze_brightness, step=2):")
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
    # 释放
    del test_data
    gc.collect()

    # 测试新增生成函数（逐个生成并演示）
    print("\n2. 生成测试图片函数测试:")

    # 2.1 均匀图
    print("  - 均匀图 (value=128):")
    img = create_uniform_image(10, 10, 128)
    print(f"    长度: {len(img)}, 前5个值: {img[:5]}")
    del img
    gc.collect()

    # 2.2 渐变图
    grad_h = create_gradient_image(10, 10, 'horizontal')
    print("  - 水平渐变图: 首行前5个值:", grad_h[:5])
    del grad_h
    grad_v = create_gradient_image(10, 10, 'vertical')
    print("  - 垂直渐变图: 前5个值 (第一列):", grad_v[0], grad_v[10], grad_v[20], grad_v[30], grad_v[40])
    del grad_v
    gc.collect()

    # 2.3 棋盘格
    checker = create_checkerboard_image(10, 10, 3)
    print("  - 棋盘格 (10x10, block=3): 首行前5个值:", checker[:5])
    del checker
    gc.collect()

    # 2.4 中心亮
    center_bright = create_center_bright_image(10, 10, 0.3, 200, 50)
    print("  - 中心亮图 (10x10): 中心点值 (索引 5*10+5=55):", center_bright[55])
    print("    角落值 (索引 0):", center_bright[0])
    del center_bright
    gc.collect()

    # 2.5 中心暗
    center_dark = create_center_dark_image(10, 10, 0.3, 50, 200)
    print("  - 中心暗图 (10x10): 中心点值 (索引 55):", center_dark[55])
    print("    角落值 (索引 0):", center_dark[0])
    del center_dark
    gc.collect()

    # 2.6 多彩模拟（3x3 不同灰度块）
    print("  - 多彩区域模拟 (3x3 不同灰度块):")
    multi_data = bytearray(30 * 30)
    for y in range(30):
        for x in range(30):
            cell_x = x // 10
            cell_y = y // 10
            values = [40, 120, 200, 80, 160, 240, 30, 100, 180]
            multi_data[y*30 + x] = values[cell_y * 3 + cell_x]
    print("    中心区域 (10x10) 的首行值:", multi_data[10*30:10*30+10])
    del multi_data
    gc.collect()

    # 3. 使用生成图片进行亮度分析（逐个生成并分析）
    print("\n3. 使用生成图片进行亮度分析:")
    test_img = create_gradient_image(320, 240, 'horizontal')
    result = analyze_brightness(test_img, 320, 240, step=2)
    if result:
        print(f"  水平渐变图: avg={result['average_brightness']:.1f}, dynamic={result['dynamic_range']}")
    del test_img
    gc.collect()

    # 4. 加载文件测试（如果有图片文件）
    try:
        import uos
        files = uos.listdir('/sd')
        jpg_files = [f for f in files if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
        if jpg_files:
            test_file = '/sd/' + jpg_files[0]
            print("\n4. 加载图片文件测试:")
            img_data = load_image_from_file(test_file)
            if img_data:
                info = get_image_info(img_data)
                print(f"  文件: {test_file}, 大小: {info['size_bytes']} bytes, 格式: {info['format']}")
                if info['is_jpeg']:
                    print("  (JPEG 文件加载成功，可用于保存或传输)")
                del img_data
                gc.collect()
            else:
                print("  加载文件失败")
        else:
            print("\n4. 未在 /sd 找到 JPEG 文件，跳过加载测试")
    except Exception as e:
        print("\n4. 加载测试失败:", e)

    print("\n✅ utils 工具测试完成")