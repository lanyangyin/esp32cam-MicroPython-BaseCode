# main.py
from photo_capturer import PhotoCapturer
import camera

def main():
    # 1. 创建拍照器实例（可配置引脚、挂载点、摄像头参数）
    capturer = PhotoCapturer(
        flash_pin=4,
        flash_on_value=0,          # 低电平点亮（视硬件而定）
        sd_mount_point="/sd",
        camera_params={
            "framesize": camera.FRAME_XGA,   # 1024x768
            "quality": 10,                   # 数值越小画质越好
            "flip": 1,                       # 上下翻转
            "mirror": 0,
            "whitebalance": camera.WB_CLOUDY,
        }
    )

    # 2. 拍照并自动保存（文件名自动生成时间戳）
    saved_path = capturer.take_photo(
        pre_flash_delay=200,       # 开灯后等待 200ms
        auto_deinit=True           # 拍完释放摄像头
    )

    if saved_path:
        print("✅ Photo saved:", saved_path)
    else:
        print("❌ Failed to take photo")

    # 3. 释放闪光灯（已自动关闭）
    capturer.cleanup()

if __name__ == "__main__":
    main()