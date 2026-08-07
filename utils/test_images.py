# utils/test_images.py
"""
生成各种灰度测试图像（均匀、渐变、棋盘格、中心亮/暗等）
"""

def create_uniform_image(width, height, value=128):
    if width <= 0 or height <= 0 or not (0 <= value <= 255):
        return None
    return bytes([value]) * (width * height)


def create_gradient_image(width, height, direction='horizontal'):
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
    if width <= 0 or height <= 0 or block_size <= 0:
        return None
    data = bytearray(width * height)
    for y in range(height):
        row_start = y * width
        for x in range(width):
            cell_x = x // block_size
            cell_y = y // block_size
            value = 255 if (cell_x + cell_y) % 2 == 0 else 0
            data[row_start + x] = value
    return bytes(data)


def create_center_bright_image(width, height, center_radius_ratio=0.3,
                               center_value=200, surround_value=50):
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
    return create_center_bright_image(width, height, center_radius_ratio,
                                      center_value, surround_value)


# ---------- 独立测试 ----------
if __name__ == "__main__":
    print("\n--- test_images 模块测试 ---")
    img = create_uniform_image(10, 10, 128)
    print("均匀图长度:", len(img))
    grad = create_gradient_image(10, 10, 'horizontal')
    print("水平渐变首行:", grad[:5])
    checker = create_checkerboard_image(10, 10, 3)
    print("棋盘格首行:", checker[:5])
    bright = create_center_bright_image(10, 10)
    print("中心亮图中心点值:", bright[55])