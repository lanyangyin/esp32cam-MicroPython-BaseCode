# utils/image_encoders.py
"""
图像格式编码器（纯算法，无文件 I/O）
将摄像头原始格式（RGB565/GRAYSCALE）编码为标准的 BMP/PPM/RAW 字节流。
"""
import struct


def encode_rgb565_to_bmp(rgb565_data, width, height):
    """
    将 RGB565 原始数据编码为 24位 BMP 字节流（含文件头）。
    返回 bytes 对象，可直接写入 .bmp 文件。
    """
    if not rgb565_data or len(rgb565_data) < width * height * 2:
        return None

    # 每行字节数（4字节对齐）
    row_stride = (width * 3 + 3) & ~3
    pixel_data_size = row_stride * height
    file_size = 14 + 40 + pixel_data_size

    # ---------- 构造 BMP 文件头 (14 bytes) ----------
    header = bytearray(14 + 40)
    # BITMAPFILEHEADER
    header[0:2] = b'BM'
    struct.pack_into('<I', header, 2, file_size)  # bfSize
    struct.pack_into('<I', header, 6, 0)  # bfReserved
    struct.pack_into('<I', header, 10, 14 + 40)  # bfOffBits

    # BITMAPINFOHEADER (40 bytes)
    struct.pack_into('<I', header, 14, 40)  # biSize
    struct.pack_into('<I', header, 18, width)  # biWidth
    struct.pack_into('<I', header, 22, height)  # biHeight (正值表示自下而上)
    struct.pack_into('<H', header, 26, 1)  # biPlanes
    struct.pack_into('<H', header, 28, 24)  # biBitCount
    struct.pack_into('<I', header, 30, 0)  # biCompression (BI_RGB)
    struct.pack_into('<I', header, 34, pixel_data_size)
    struct.pack_into('<I', header, 38, 0)  # biXPelsPerMeter
    struct.pack_into('<I', header, 42, 0)  # biYPelsPerMeter
    struct.pack_into('<I', header, 46, 0)  # biClrUsed
    struct.pack_into('<I', header, 50, 0)  # biClrImportant

    # ---------- 转换像素 (BGR) ----------
    pixel_data = bytearray(row_stride * height)
    idx_in = 0
    # BMP 标准存储为自下而上（Bottom-Up），我们按行反转
    for y in range(height - 1, -1, -1):
        row_start = y * row_stride
        for x in range(width):
            pixel = (rgb565_data[idx_in + 1] << 8) | rgb565_data[idx_in]
            idx_in += 2

            r = (pixel >> 11) & 0x1F
            r = (r << 3) | (r >> 2)
            g = (pixel >> 5) & 0x3F
            g = (g << 2) | (g >> 4)
            b = pixel & 0x1F
            b = (b << 3) | (b >> 2)

            offset = row_start + x * 3
            pixel_data[offset] = b
            pixel_data[offset + 1] = g
            pixel_data[offset + 2] = r

    return bytes(header) + pixel_data


def encode_rgb565_to_ppm(rgb565_data, width, height):
    """
    将 RGB565 原始数据编码为 PPM (P6) 字节流。
    返回 bytes 对象，可直接写入 .ppm 文件。
    """
    if not rgb565_data or len(rgb565_data) < width * height * 2:
        return None

    header = "P6\n{} {}\n255\n".format(width, height).encode()
    pixel_data = bytearray(width * height * 3)

    idx_in = 0
    idx_out = 0
    for _ in range(width * height):
        pixel = (rgb565_data[idx_in + 1] << 8) | rgb565_data[idx_in]
        idx_in += 2

        r = (pixel >> 11) & 0x1F
        r = (r << 3) | (r >> 2)
        g = (pixel >> 5) & 0x3F
        g = (g << 2) | (g >> 4)
        b = pixel & 0x1F
        b = (b << 3) | (b >> 2)

        pixel_data[idx_out] = r
        pixel_data[idx_out + 1] = g
        pixel_data[idx_out + 2] = b
        idx_out += 3

    return header + pixel_data


def encode_grayscale_to_pgm(gray_data, width, height):
    """
    将灰度原始数据编码为 PGM (P5) 字节流。
    返回 bytes 对象，可直接写入 .pgm 文件。
    """
    if not gray_data or len(gray_data) < width * height:
        return None
    header = "P5\n{} {}\n255\n".format(width, height).encode()
    return header + gray_data


def encode_grayscale_to_raw(gray_data):
    """
    灰度原始数据直接返回（不加头）。
    主要用于快速存储或程序间传输。
    """
    return gray_data