# utils/image_info.py
"""
图片格式解析和尺寸提取
"""
import struct

def get_image_info(image_data):
    """
    获取图片的详细元信息（支持 JPEG/PNG）。
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

    if image_data[0:2] == b'\xff\xd8':
        result['format'] = 'JPEG'
        result['is_jpeg'] = True
        w, h = _parse_jpeg_dimensions(image_data)
        if w and h:
            result['width'] = w
            result['height'] = h

    elif image_data[0:8] == b'\x89PNG\r\n\x1a\n':
        result['format'] = 'PNG'
        result['is_png'] = True
        if len(image_data) >= 24:
            w, h = struct.unpack('>II', image_data[16:24])
            result['width'] = w
            result['height'] = h

    return result


def get_image_size(image_data):
    """获取图片文件大小（字节）"""
    return len(image_data) if image_data else 0


def get_image_dimensions(image_data):
    """获取图片尺寸 (width, height)"""
    info = get_image_info(image_data)
    return (info['width'], info['height']) if info else (0, 0)


def _parse_jpeg_dimensions(jpeg_data):
    """
    从 JPEG 数据中解析宽度和高度。
    遍历标记，查找 SOF0 (0xFFC0) 或 SOF2 (0xFFC2)。
    """
    idx = 0
    data_len = len(jpeg_data)
    while idx < data_len - 1:
        # 查找 0xFF
        if jpeg_data[idx] != 0xFF:
            idx += 1
            continue
        marker = jpeg_data[idx + 1]
        idx += 2

        # 忽略无长度字段的标记
        if marker == 0xD8 or (0xD0 <= marker <= 0xD7) or marker == 0x01:
            continue
        if marker == 0xD9:  # EOI
            break

        # 读取段长度（大端）
        if idx + 1 >= data_len:
            break
        seg_len = (jpeg_data[idx] << 8) + jpeg_data[idx + 1]
        idx += 2

        # 如果是 SOF0 或 SOF2，提取尺寸
        if marker == 0xC0 or marker == 0xC2:
            if idx + 5 <= data_len:
                height = (jpeg_data[idx + 1] << 8) + jpeg_data[idx + 2]
                width = (jpeg_data[idx + 3] << 8) + jpeg_data[idx + 4]
                return (width, height)
            else:
                return (0, 0)

        # 跳过段数据
        idx += seg_len - 2  # 减去已经读的长度字段

    return (0, 0)


# ---------- 独立测试 ----------
if __name__ == "__main__":
    # 生成简单的 JPEG 模拟数据（无法实际解析，仅演示）
    print("\n--- image_info 模块测试 ---")
    # 因为没有真实图片，跳过测试，仅打印说明
    print("本模块需要真实图片数据进行测试。")