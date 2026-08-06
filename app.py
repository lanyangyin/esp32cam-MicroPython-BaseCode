# app.py
from photo_capturer import PhotoCapturer
import camera_analyzer
import camera

def main():
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

    # 方式1：仅拍照，不带分析
    # saved_path = capturer.take_photo()

    # 方式2：拍照并分析环境光
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



    result = camera_analyzer.analyze_brightness_from_camera(
        framesize=camera.FRAME_XGA,
        flash_off=True,          # 关闭闪光灯测环境光
        flash_pin=4,
        flash_on_value=1         # 根据你的硬件调整
    )

    if result:
        print(f"环境亮度: {result['average_brightness']:.1f}")
        print(f"动态范围: {result['dynamic_range']}")
        print(f"主体亮度: {result['center_brightness']:.1f}")
    else:
        print("分析失败")

if __name__ == "__main__":
    main()