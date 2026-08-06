# app.py
from photo_capturer import PhotoCapturer
import camera
import camera_analyzer

def main():
    """
    主程序：演示三种拍照/分析模式。
    1. 仅拍照（不分析）
    2. 拍照并分析环境光（先分析后拍照）
    3. 独立环境光分析（不拍照）
    """
    # ---------- 1. 仅拍照 ----------
    print("\n--- 1. 仅拍照 ---")
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=1,
        sd_mount_point="/sd",
        camera_params={
            "framesize": camera.FRAME_XGA,
            "quality": 10,
            "flip": 1,
            "whitebalance": camera.WB_CLOUDY,
        }
    )
    saved_path = capturer.take_photo(pre_flash_delay=200, auto_deinit=True)
    if saved_path:
        print("✅ Photo saved:", saved_path)
    else:
        print("❌ Failed")
    capturer.cleanup()

    # ---------- 2. 拍照并分析 ----------
    print("\n--- 2. 拍照并分析 ---")
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=1,
        sd_mount_point="/sd",
        camera_params={
            "framesize": camera.FRAME_XGA,
            "quality": 10,
            "flip": 1,
            "whitebalance": camera.WB_CLOUDY,
        }
    )
    saved_path, analysis = capturer.take_photo_with_analysis()
    if saved_path:
        print("✅ Photo saved:", saved_path)
        if analysis:
            print("📊 Analysis:")
            print(f"  Average brightness: {analysis['average_brightness']:.1f}")
            print(f"  Dynamic range: {analysis['dynamic_range']}")
            print(f"  Center brightness: {analysis['center_brightness']:.1f}")
    else:
        print("❌ Failed")
    capturer.cleanup()

    # ---------- 3. 独立环境光分析 ----------
    print("\n--- 3. 独立环境光分析 ---")
    result = camera_analyzer.analyze_brightness_from_camera(
        framesize=camera.FRAME_XGA,
        flash_off=True,
        flash_pin=4,
        flash_on_value=1
    )
    if result:
        print(f"环境亮度: {result['average_brightness']:.1f}")
        print(f"动态范围: {result['dynamic_range']}")
        print(f"主体亮度: {result['center_brightness']:.1f}")
    else:
        print("分析失败")

if __name__ == "__main__":
    main()