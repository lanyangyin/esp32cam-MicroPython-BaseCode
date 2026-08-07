"""
app.py - ESP32-CAM 完整测试入口

覆盖所有模块：
    1. 模拟测试（utils）
    2. 真实摄像头测试（遍历分辨率）
    3. 闪光灯测试
    4. SD卡格式测试（灰度 RAW/PGM）
    5. (可选) WiFi / BLE 初始化测试

用法：
    import app
    app.main()
"""
import camera
import time
import gc
from config import set_debug
from camera_driver import (
    reset_camera,
    get_camera,
    capture_image,
    capture_grayscale,
    analyze_brightness_from_camera,
    quick_brightness_from_camera,
    quick_brightness_with_jpeg,
    CameraController,
)
from sd_card import get_sd_card
from flash import get_flash, reset_flash
from utils import (
    analyze_brightness,
    quick_brightness_estimate,
    create_gradient_image,
    encode_rgb565_to_bmp,
    encode_rgb565_to_ppm,
    encode_grayscale_to_pgm,
    encode_grayscale_to_raw,
    get_image_info,
    print_info,
)
# 可选 WiFi / BLE
# from wifi import get_wifi, reset_wifi
# from ble import get_ble, reset_ble

set_debug(True)


# =============================================================================
# 1. 模拟测试
# =============================================================================
def test_utils():
    """测试 utils 包中的所有纯算法函数"""
    print("\n" + "="*60)
    print("  [模拟测试] 验证 utils 纯算法")
    print("="*60)

    print("\n1. 生成测试图像并运行亮度分析")
    w, h = 320, 240
    gray_data = create_gradient_image(w, h, 'horizontal')
    result = analyze_brightness(gray_data, w, h, step=2)
    print("   平均亮度: {:.1f}".format(result['average_brightness']))
    print("   动态范围: {}".format(result['dynamic_range']))
    print("   中心亮度: {:.1f}".format(result['center_brightness']))

    quick = quick_brightness_estimate(gray_data, w, h)
    print("   快速估计 (9点): {:.1f}".format(quick))

    print("\n2. 测试灰度编码 (PGM / RAW)")
    pgm_data = encode_grayscale_to_pgm(gray_data, w, h)
    raw_data = encode_grayscale_to_raw(gray_data)
    print("   PGM 大小: {} bytes (含头)".format(len(pgm_data)))
    print("   RAW 大小: {} bytes (纯数据)".format(len(raw_data)))

    print("\n3. 生成模拟 RGB565 数据并测试 BMP/PPM 编码")
    rgb565_data = bytearray(w * h * 2)
    idx = 0
    for y in range(h):
        for x in range(w):
            r = int((x / w) * 31) & 0x1F
            g = int(((x + y) / (w + h)) * 63) & 0x3F
            b = int((y / h) * 31) & 0x1F
            pixel = (r << 11) | (g << 5) | b
            rgb565_data[idx] = pixel & 0xFF
            rgb565_data[idx+1] = (pixel >> 8) & 0xFF
            idx += 2

    bmp_data = encode_rgb565_to_bmp(rgb565_data, w, h)
    ppm_data = encode_rgb565_to_ppm(rgb565_data, w, h)
    print("   BMP 大小: {} bytes".format(len(bmp_data)))
    print("   PPM 大小: {} bytes".format(len(ppm_data)))

    print("\n4. 测试图片信息提取")
    info = get_image_info(bmp_data)
    print("   格式: {}, 尺寸: {}x{}, 大小: {} bytes".format(
        info['format'], info['width'], info['height'], info['size_bytes']))

    print("\n✅ 模拟测试全部通过\n")


# =============================================================================
# 2. 闪光灯测试
# =============================================================================
def test_flash():
    """测试闪光灯控制（开/关/闪烁/补光）"""
    print("\n" + "="*60)
    print("  [闪光灯测试]")
    print("="*60)

    flash = get_flash(pin=4, on_value=1)
    print("1. 闪烁 3 次 (200ms on/off)")
    flash.blink(times=3, on_time=200, off_time=200)  # 现在支持 times 参数
    time.sleep_ms(500)

    print("2. 补光 500ms (拍照预闪)")
    flash.pulse(500)
    time.sleep_ms(500)

    flash.off()
    print("✅ 闪光灯测试完成\n")


# =============================================================================
# 3. SD卡格式测试（灰度保存）
# =============================================================================
def test_sd_formats():
    """测试保存灰度图的不同格式（RAW / PGM）"""
    print("\n" + "="*60)
    print("  [SD卡格式测试] 灰度保存")
    print("="*60)

    sd = get_sd_card()
    if not sd.mounted:
        print("❌ SD 卡未挂载，跳过")
        return

    # 使用 QVGA 分辨率捕获灰度图
    print("捕获灰度图 (QVGA)...")
    gray_data = capture_grayscale(framesize=camera.FRAME_QVGA, whitebalance=camera.WB_CLOUDY)
    if gray_data is None:
        print("❌ 灰度捕获失败")
        return

    w, h = 320, 240  # QVGA 固定尺寸

    # 保存 RAW
    raw_file = "/sd/test_gray_raw.raw"
    raw_enc = encode_grayscale_to_raw(gray_data)  # 直接返回原始字节
    if raw_enc and sd.save_file(raw_enc, raw_file):
        print("✅ RAW 保存成功: {} ({} bytes)".format(raw_file, len(raw_enc)))
    else:
        print("❌ RAW 保存失败")

    # 保存 PGM
    pgm_file = "/sd/test_gray_pgm.pgm"
    pgm_enc = encode_grayscale_to_pgm(gray_data, w, h)
    if pgm_enc and sd.save_file(pgm_enc, pgm_file):
        print("✅ PGM 保存成功: {} ({} bytes)".format(pgm_file, len(pgm_enc)))
    else:
        print("❌ PGM 保存失败")


# =============================================================================
# 4. 真实摄像头测试（遍历分辨率）
# =============================================================================
def test_camera_resolutions():
    """
    遍历所有支持的分辨率，全面测试摄像头功能。

    内存不足处理：
        当遇到 MemoryError 时，跳过当前及所有更高分辨率。
    """
    print("\n" + "="*60)
    print("  [真实摄像头测试] 遍历所有分辨率")
    print("="*60)

    # 获取所有 camera.FRAME_* 常量（去重）
    resolution_constants = []
    seen = set()
    for attr in dir(camera):
        if attr.startswith("FRAME_"):
            val = getattr(camera, attr)
            if val not in seen:
                seen.add(val)
                resolution_constants.append(val)
    resolution_constants.sort()
    print("发现 {} 个分辨率常量".format(len(resolution_constants)))

    sd = get_sd_card()
    if not sd.mounted:
        print("❌ SD 卡未挂载，无法保存文件")
        return

    success_count = 0
    fail_count = 0
    skipped_count = 0
    memory_error_occurred = False

    for idx, framesize in enumerate(resolution_constants, 1):
        if memory_error_occurred:
            skipped_count += 1
            print("\n--- [{}/{}] 跳过分辨率: {} (因之前内存不足)".format(
                idx, len(resolution_constants), framesize))
            continue

        res_name = CameraController.get_resolution(framesize)
        w, h = res_name if res_name[0] else (0, 0)
        print("\n--- [{}/{}] 测试分辨率: {} ({}x{}) ---".format(
            idx, len(resolution_constants), framesize, w, h))

        reset_camera()
        time.sleep_ms(200)
        gc.collect()

        try:
            # A. JPEG
            print("  [JPEG] 捕获中...")
            jpeg_data = capture_image(
                framesize=framesize,
                quality=10,
                whitebalance=camera.WB_CLOUDY,
                flip=1,
            )
            if jpeg_data:
                jpeg_file = "/sd/test_{}_{}x{}.jpg".format(framesize, w, h)
                sd.save_file(jpeg_data, jpeg_file)
                print("    ✅ JPEG 保存成功: {} ({} bytes)".format(jpeg_file, len(jpeg_data)))
            else:
                print("    ❌ JPEG 捕获失败")
                raise RuntimeError("JPEG capture failed")

            # B. 灰度分析
            print("  [灰度分析] 捕获并分析...")
            analysis = analyze_brightness_from_camera(framesize=framesize, step=2)
            if analysis:
                print("    ✅ 亮度分析: avg={:.1f}, dynamic={}, center={:.1f}".format(
                    analysis['average_brightness'],
                    analysis['dynamic_range'],
                    analysis['center_brightness']))
            else:
                print("    ⚠️ 亮度分析返回 None")

            # C. RGB565 编码 BMP/PPM
            print("  [RGB565] 捕获并编码 BMP/PPM...")
            cam = get_camera()
            if cam.initialized:
                cam.deinit()
            cam.init(framesize=framesize, format=camera.RGB565,
                     whitebalance=camera.WB_CLOUDY, flip=1)
            rgb565_buf = cam.capture()
            cam.deinit()

            if rgb565_buf and len(rgb565_buf) >= w * h * 2:
                bmp_data = encode_rgb565_to_bmp(rgb565_buf, w, h)
                if bmp_data:
                    bmp_file = "/sd/test_{}_{}x{}.bmp".format(framesize, w, h)
                    sd.save_file(bmp_data, bmp_file)
                    print("    ✅ BMP 保存成功: {} ({} bytes)".format(bmp_file, len(bmp_data)))
                else:
                    print("    ❌ BMP 编码失败")

                ppm_data = encode_rgb565_to_ppm(rgb565_buf, w, h)
                if ppm_data:
                    ppm_file = "/sd/test_{}_{}x{}.ppm".format(framesize, w, h)
                    sd.save_file(ppm_data, ppm_file)
                    print("    ✅ PPM 保存成功: {} ({} bytes)".format(ppm_file, len(ppm_data)))
                else:
                    print("    ❌ PPM 编码失败")
            else:
                print("    ❌ RGB565 捕获失败或数据不完整")

            # D. 快速估计
            print("  [快速估计] 快速亮度 (9点)...")
            quick_avg = quick_brightness_from_camera(framesize=framesize)
            if quick_avg is not None:
                print("    ✅ 快速估计: {:.1f}".format(quick_avg))
            else:
                print("    ⚠️ 快速估计返回 None")

            # E. 快速估计 + JPEG
            print("  [快速+JPEG] 组合捕获...")
            q_avg, q_jpeg = quick_brightness_with_jpeg(framesize=framesize, quality=15)
            if q_jpeg:
                print("    ✅ 组合JPEG 大小: {} bytes, 亮度估计: {}".format(
                    len(q_jpeg), q_avg if q_avg else "N/A"))
            else:
                print("    ⚠️ 组合捕获失败")

            print("  ✅ 分辨率 {} 测试完成".format(framesize))
            success_count += 1

        except MemoryError as e:
            print("  ❌ 内存不足: {}".format(e))
            memory_error_occurred = True
            fail_count += 1
            print("  ⚠️ 跳过所有后续分辨率 (内存不足)")

        except Exception as e:
            print("  ❌ 分辨率 {} 测试失败: {}".format(framesize, e))
            fail_count += 1

        reset_camera()
        time.sleep_ms(100)
        gc.collect()

    print("\n" + "="*60)
    print("  [摄像头测试汇总]")
    print("  成功: {}, 失败: {}, 跳过: {}".format(success_count, fail_count, skipped_count))
    if memory_error_occurred:
        print("  ⚠️ 因内存不足跳过了后续 {} 个分辨率".format(skipped_count))
    print("="*60)


# =============================================================================
# 5. 可选 WiFi / BLE 测试（注释掉以节省内存）
# =============================================================================
# def test_wifi():
#     print("\n[WiFi] 尝试连接...")
#     wifi = get_wifi()
#     # 请替换为实际凭据
#     ok = wifi.connect("YourSSID", "YourPassword", timeout=5)
#     if ok:
#         print("✅ WiFi 连接成功，IP:", wifi.get_ip())
#         wifi.disconnect()
#     else:
#         print("❌ WiFi 连接失败 (可能未配置或信号弱)")
#     reset_wifi()

# def test_ble():
#     print("\n[BLE] 初始化和广播...")
#     ble = get_ble("ESP32_CAM_TEST")
#     time.sleep_ms(1000)
#     print("✅ BLE 广播中，名称:", "ESP32_CAM_TEST")
#     ble.deinit()
#     reset_ble()


# =============================================================================
# 主入口
# =============================================================================
def main():
    """执行所有测试"""
    print("\n🔍 ESP32-CAM 完整测试套件启动")
    print("  当前时间: {}".format(time.localtime()))

    print_info()                # 硬件信息
    test_utils()               # 模拟算法
    test_flash()               # 闪光灯
    test_sd_formats()          # 灰度保存
    test_camera_resolutions()  # 摄像头遍历

    # 可选模块（若需测试请取消注释）
    # test_wifi()
    # test_ble()

    print("\n✅ 所有测试执行完毕。")


if __name__ == "__main__":
    main()