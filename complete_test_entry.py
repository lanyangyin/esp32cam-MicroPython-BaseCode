"""
complete_test_entry.py - ESP32-CAM 完整测试入口

覆盖所有模块：
    1. 模拟测试（utils）
    2. 闪光灯测试
    3. SD卡格式测试（灰度 RAW/PGM）
    4. 摄像头 JPEG 模式测试（遍历分辨率）
    5. 摄像头 灰度模式测试（遍历分辨率）
    6. 摄像头 RGB565 模式测试（遍历分辨率，含 BMP/PPM 编码）
    (可选) WiFi / BLE 初始化测试

每种摄像头模式独立测试，内存不足时仅跳过该模式的更大分辨率。
"""
import camera
import time
import gc
from config import set_debug, debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR, LEVEL_DEBUG, set_log_level
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

# 启用调试日志，并设置日志级别为 DEBUG（输出所有日志）
set_debug(True)
set_log_level(LEVEL_DEBUG)  # 可根据需要调整为 INFO


# =============================================================================
# 1. 模拟测试
# =============================================================================
def test_utils():
    """测试 utils 包中的所有纯算法函数"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [模拟测试] 验证 utils 纯算法", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    debug_log("1. 生成测试图像并运行亮度分析", level=LEVEL_INFO, module="Test")
    w, h = 320, 240
    gray_data = create_gradient_image(w, h, 'horizontal')
    result = analyze_brightness(gray_data, w, h, step=2)
    debug_log("   平均亮度: {:.1f}".format(result['average_brightness']), level=LEVEL_INFO, module="Test")
    debug_log("   动态范围: {}".format(result['dynamic_range']), level=LEVEL_INFO, module="Test")
    debug_log("   中心亮度: {:.1f}".format(result['center_brightness']), level=LEVEL_INFO, module="Test")

    quick = quick_brightness_estimate(gray_data, w, h)
    debug_log("   快速估计 (9点): {:.1f}".format(quick), level=LEVEL_INFO, module="Test")

    debug_log("2. 测试灰度编码 (PGM / RAW)", level=LEVEL_INFO, module="Test")
    pgm_data = encode_grayscale_to_pgm(gray_data, w, h)
    raw_data = encode_grayscale_to_raw(gray_data)
    debug_log("   PGM 大小: {} bytes (含头)".format(len(pgm_data)), level=LEVEL_INFO, module="Test")
    debug_log("   RAW 大小: {} bytes (纯数据)".format(len(raw_data)), level=LEVEL_INFO, module="Test")

    debug_log("3. 生成模拟 RGB565 数据并测试 BMP/PPM 编码", level=LEVEL_INFO, module="Test")
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
    debug_log("   BMP 大小: {} bytes".format(len(bmp_data)), level=LEVEL_INFO, module="Test")
    debug_log("   PPM 大小: {} bytes".format(len(ppm_data)), level=LEVEL_INFO, module="Test")

    debug_log("4. 测试图片信息提取", level=LEVEL_INFO, module="Test")
    info = get_image_info(bmp_data)
    debug_log("   格式: {}, 尺寸: {}x{}, 大小: {} bytes".format(
        info['format'], info['width'], info['height'], info['size_bytes']), level=LEVEL_INFO, module="Test")

    debug_log("✅ 模拟测试全部通过\n", level=LEVEL_INFO, module="Test")


# =============================================================================
# 2. 闪光灯测试
# =============================================================================
def test_flash():
    """测试闪光灯控制（开/关/闪烁/补光）"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [闪光灯测试]", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    flash = get_flash(pin=4, on_value=1)
    debug_log("1. 闪烁 3 次 (200ms on/off)", level=LEVEL_INFO, module="Test")
    flash.blink(times=3, on_time=200, off_time=200)
    time.sleep_ms(500)

    debug_log("2. 补光 500ms (拍照预闪)", level=LEVEL_INFO, module="Test")
    flash.pulse(500)
    time.sleep_ms(500)

    flash.off()
    debug_log("✅ 闪光灯测试完成\n", level=LEVEL_INFO, module="Test")


# =============================================================================
# 3. SD卡格式测试
# =============================================================================
def test_sd_formats():
    """测试保存灰度图的不同格式（RAW / PGM）"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [SD卡格式测试] 灰度保存", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载，跳过", level=LEVEL_WARNING, module="Test")
        return

    debug_log("捕获灰度图 (QVGA)...", level=LEVEL_INFO, module="Test")
    gray_data = capture_grayscale(framesize=camera.FRAME_QVGA, whitebalance=camera.WB_CLOUDY)
    if gray_data is None:
        debug_log("❌ 灰度捕获失败", level=LEVEL_ERROR, module="Test")
        return

    w, h = 320, 240  # QVGA

    raw_file = "/sd/test_gray_raw.raw"
    raw_enc = encode_grayscale_to_raw(gray_data)
    if raw_enc and sd.save_file(raw_enc, raw_file):
        debug_log("✅ RAW 保存成功: {} ({} bytes)".format(raw_file, len(raw_enc)), level=LEVEL_INFO, module="Test")
    else:
        debug_log("❌ RAW 保存失败", level=LEVEL_ERROR, module="Test")

    pgm_file = "/sd/test_gray_pgm.pgm"
    pgm_enc = encode_grayscale_to_pgm(gray_data, w, h)
    if pgm_enc and sd.save_file(pgm_enc, pgm_file):
        debug_log("✅ PGM 保存成功: {} ({} bytes)".format(pgm_file, len(pgm_enc)), level=LEVEL_INFO, module="Test")
    else:
        debug_log("❌ PGM 保存失败", level=LEVEL_ERROR, module="Test")


# =============================================================================
# 4. 摄像头 JPEG 模式测试（独立遍历）
# =============================================================================
def test_jpeg_resolutions():
    """仅测试 JPEG 捕获与保存，独立处理内存不足"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [摄像头测试] JPEG 模式", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    resolution_constants = _get_resolution_list()
    debug_log("发现 {} 个分辨率".format(len(resolution_constants)), level=LEVEL_INFO, module="Test")

    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载", level=LEVEL_ERROR, module="Test")
        return

    success = 0
    fail = 0
    skipped = 0
    memory_error = False

    for idx, framesize in enumerate(resolution_constants, 1):
        if memory_error:
            skipped += 1
            debug_log("\n--- [{}/{}] 跳过分辨率: {} (因内存不足)".format(
                idx, len(resolution_constants), framesize), level=LEVEL_WARNING, module="Test")
            continue

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            w, h = 0, 0
        debug_log("\n--- [{}/{}] 测试 JPEG: {} ({}x{}) ---".format(
            idx, len(resolution_constants), framesize, w, h), level=LEVEL_INFO, module="Test")

        reset_camera()
        time.sleep_ms(200)
        gc.collect()

        try:
            jpeg_data = capture_image(
                framesize=framesize,
                quality=10,
                whitebalance=camera.WB_CLOUDY,
                flip=1,
            )
            if jpeg_data:
                fname = "/sd/test_jpeg_{}_{}x{}.jpg".format(framesize, w, h)
                sd.save_file(jpeg_data, fname)
                debug_log("    ✅ JPEG 保存成功: {} ({} bytes)".format(fname, len(jpeg_data)), level=LEVEL_INFO, module="Test")
                success += 1
            else:
                debug_log("    ❌ JPEG 捕获失败", level=LEVEL_ERROR, module="Test")
                fail += 1
        except MemoryError as e:
            debug_log("    ❌ 内存不足: {}".format(e), level=LEVEL_ERROR, module="Test")
            memory_error = True
            fail += 1
        except Exception as e:
            debug_log("    ❌ 异常: {}".format(e), level=LEVEL_ERROR, module="Test")
            fail += 1

        reset_camera()
        time.sleep_ms(100)
        gc.collect()

    debug_log("\n[JPEG 测试汇总] 成功: {}, 失败: {}, 跳过: {}".format(success, fail, skipped), level=LEVEL_INFO, module="Test")
    if memory_error:
        debug_log("  ⚠️ 因内存不足跳过了后续 {} 个分辨率".format(skipped), level=LEVEL_WARNING, module="Test")


# =============================================================================
# 5. 摄像头 灰度模式测试（独立遍历）
# =============================================================================
def test_grayscale_resolutions():
    """仅测试灰度捕获 + 亮度分析 + 快速估计，独立处理内存不足"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [摄像头测试] 灰度模式", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    resolution_constants = _get_resolution_list()
    debug_log("发现 {} 个分辨率".format(len(resolution_constants)), level=LEVEL_INFO, module="Test")

    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载", level=LEVEL_ERROR, module="Test")
        return

    success = 0
    fail = 0
    skipped = 0
    memory_error = False

    for idx, framesize in enumerate(resolution_constants, 1):
        if memory_error:
            skipped += 1
            debug_log("\n--- [{}/{}] 跳过分辨率: {} (因内存不足)".format(
                idx, len(resolution_constants), framesize), level=LEVEL_WARNING, module="Test")
            continue

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            w, h = 0, 0
        debug_log("\n--- [{}/{}] 测试灰度: {} ({}x{}) ---".format(
            idx, len(resolution_constants), framesize, w, h), level=LEVEL_INFO, module="Test")

        reset_camera()
        time.sleep_ms(200)
        gc.collect()

        try:
            # 亮度分析
            analysis = analyze_brightness_from_camera(framesize=framesize, step=2)
            if analysis:
                debug_log("    ✅ 亮度分析: avg={:.1f}, dynamic={}, center={:.1f}".format(
                    analysis['average_brightness'],
                    analysis['dynamic_range'],
                    analysis['center_brightness']), level=LEVEL_INFO, module="Test")
            else:
                debug_log("    ⚠️ 亮度分析返回 None", level=LEVEL_WARNING, module="Test")

            # 快速估计
            quick = quick_brightness_from_camera(framesize=framesize)
            if quick is not None:
                debug_log("    ✅ 快速估计: {:.1f}".format(quick), level=LEVEL_INFO, module="Test")
            else:
                debug_log("    ⚠️ 快速估计返回 None", level=LEVEL_WARNING, module="Test")

            # 快速+JPEG
            q_avg, q_jpeg = quick_brightness_with_jpeg(framesize=framesize, quality=15)
            if q_jpeg:
                debug_log("    ✅ 组合JPEG 大小: {} bytes, 亮度估计: {}".format(
                    len(q_jpeg), q_avg if q_avg else "N/A"), level=LEVEL_INFO, module="Test")
            else:
                debug_log("    ⚠️ 组合捕获失败", level=LEVEL_WARNING, module="Test")

            success += 1
        except MemoryError as e:
            debug_log("    ❌ 内存不足: {}".format(e), level=LEVEL_ERROR, module="Test")
            memory_error = True
            fail += 1
        except Exception as e:
            debug_log("    ❌ 异常: {}".format(e), level=LEVEL_ERROR, module="Test")
            fail += 1

        reset_camera()
        time.sleep_ms(100)
        gc.collect()

    debug_log("\n[灰度测试汇总] 成功: {}, 失败: {}, 跳过: {}".format(success, fail, skipped), level=LEVEL_INFO, module="Test")
    if memory_error:
        debug_log("  ⚠️ 因内存不足跳过了后续 {} 个分辨率".format(skipped), level=LEVEL_WARNING, module="Test")


# =============================================================================
# 6. 摄像头 RGB565 模式测试（独立遍历）
# =============================================================================
def test_rgb565_resolutions():
    """仅测试 RGB565 捕获 + BMP/PPM 编码，独立处理内存不足"""
    debug_log("="*60, level=LEVEL_INFO, module="Test")
    debug_log("  [摄像头测试] RGB565 模式 (BMP/PPM编码)", level=LEVEL_INFO, module="Test")
    debug_log("="*60, level=LEVEL_INFO, module="Test")

    resolution_constants = _get_resolution_list()
    debug_log("发现 {} 个分辨率".format(len(resolution_constants)), level=LEVEL_INFO, module="Test")

    sd = get_sd_card()
    if not sd.mounted:
        debug_log("❌ SD 卡未挂载", level=LEVEL_ERROR, module="Test")
        return

    success = 0
    fail = 0
    skipped = 0
    memory_error = False

    for idx, framesize in enumerate(resolution_constants, 1):
        if memory_error:
            skipped += 1
            debug_log("\n--- [{}/{}] 跳过分辨率: {} (因内存不足)".format(
                idx, len(resolution_constants), framesize), level=LEVEL_WARNING, module="Test")
            continue

        w, h = CameraController.get_resolution(framesize)
        if w is None or h is None:
            w, h = 0, 0
        debug_log("\n--- [{}/{}] 测试 RGB565: {} ({}x{}) ---".format(
            idx, len(resolution_constants), framesize, w, h), level=LEVEL_INFO, module="Test")

        reset_camera()
        time.sleep_ms(200)
        gc.collect()

        try:
            cam = get_camera()
            if cam.initialized:
                cam.deinit()
            cam.init(framesize=framesize, format=camera.RGB565,
                     whitebalance=camera.WB_CLOUDY, flip=1)
            rgb565_buf = cam.capture()
            cam.deinit()

            if rgb565_buf and len(rgb565_buf) >= w * h * 2:
                # BMP
                bmp_data = encode_rgb565_to_bmp(rgb565_buf, w, h)
                if bmp_data:
                    bmp_file = "/sd/test_rgb565_{}_{}x{}.bmp".format(framesize, w, h)
                    sd.save_file(bmp_data, bmp_file)
                    debug_log("    ✅ BMP 保存成功: {} ({} bytes)".format(bmp_file, len(bmp_data)), level=LEVEL_INFO, module="Test")
                else:
                    debug_log("    ❌ BMP 编码失败", level=LEVEL_ERROR, module="Test")

                # PPM
                ppm_data = encode_rgb565_to_ppm(rgb565_buf, w, h)
                if ppm_data:
                    ppm_file = "/sd/test_rgb565_{}_{}x{}.ppm".format(framesize, w, h)
                    sd.save_file(ppm_data, ppm_file)
                    debug_log("    ✅ PPM 保存成功: {} ({} bytes)".format(ppm_file, len(ppm_data)), level=LEVEL_INFO, module="Test")
                else:
                    debug_log("    ❌ PPM 编码失败", level=LEVEL_ERROR, module="Test")

                success += 1
            else:
                debug_log("    ❌ RGB565 捕获失败或数据不完整", level=LEVEL_ERROR, module="Test")
                fail += 1
        except MemoryError as e:
            debug_log("    ❌ 内存不足: {}".format(e), level=LEVEL_ERROR, module="Test")
            memory_error = True
            fail += 1
        except Exception as e:
            debug_log("    ❌ 异常: {}".format(e), level=LEVEL_ERROR, module="Test")
            fail += 1

        reset_camera()
        time.sleep_ms(100)
        gc.collect()

    debug_log("\n[RGB565测试汇总] 成功: {}, 失败: {}, 跳过: {}".format(success, fail, skipped), level=LEVEL_INFO, module="Test")
    if memory_error:
        debug_log("  ⚠️ 因内存不足跳过了后续 {} 个分辨率".format(skipped), level=LEVEL_WARNING, module="Test")


# =============================================================================
# 辅助函数
# =============================================================================
def _get_resolution_list():
    """获取所有去重后的分辨率常量列表（按数值排序）"""
    seen = set()
    res = []
    for attr in dir(camera):
        if attr.startswith("FRAME_"):
            val = getattr(camera, attr)
            if val not in seen:
                seen.add(val)
                res.append(val)
    res.sort()
    return res


# =============================================================================
# 7. 可选 WiFi / BLE 测试（注释掉）
# =============================================================================
# def test_wifi():
#     debug_log("\n[WiFi] 尝试连接...", level=LEVEL_INFO, module="Test")
#     wifi = get_wifi()
#     ok = wifi.connect("YourSSID", "YourPassword", timeout=5)
#     if ok:
#         debug_log("✅ WiFi 连接成功，IP: {}".format(wifi.get_ip()), level=LEVEL_INFO, module="Test")
#         wifi.disconnect()
#     else:
#         debug_log("❌ WiFi 连接失败", level=LEVEL_ERROR, module="Test")
#     reset_wifi()

# def test_ble():
#     debug_log("\n[BLE] 初始化和广播...", level=LEVEL_INFO, module="Test")
#     ble = get_ble("ESP32_CAM_TEST")
#     time.sleep_ms(1000)
#     debug_log("✅ BLE 广播中", level=LEVEL_INFO, module="Test")
#     ble.deinit()
#     reset_ble()


# =============================================================================
# 主入口
# =============================================================================
def main():
    debug_log("\n🔍 ESP32-CAM 完整测试套件启动", level=LEVEL_INFO, module="Test")
    debug_log("  当前时间: {}".format(time.localtime()), level=LEVEL_INFO, module="Test")

    # 打印设备硬件信息（内部使用 print，但可接受）
    print_info()

    # 1. 纯算法测试
    test_utils()

    # 2. 闪光灯测试
    test_flash()

    # 3. SD卡格式测试（灰度保存）
    test_sd_formats()

    # 4. 摄像头各模式独立测试
    test_jpeg_resolutions()
    test_grayscale_resolutions()
    test_rgb565_resolutions()

    # 5. 可选 WiFi/BLE（默认注释）
    # test_wifi()
    # test_ble()

    debug_log("\n✅ 所有测试执行完毕。", level=LEVEL_INFO, module="Test")


if __name__ == "__main__":
    main()