"""
app.py - ESP32-CAM 主应用程序入口

本文件是项目的应用入口，演示了三种拍照/分析模式：
1. 仅拍照（不分析）：打开闪光灯，拍一张 JPEG 并保存到 SD 卡
2. 拍照并分析环境光（先分析后拍照）：先关闭闪光灯分析环境亮度，再开灯拍照
3. 独立环境光分析（不拍照）：仅获取环境亮度数据，用于决策判断

本文件依赖以下模块：
    - photo_capturer: 提供高级拍照功能
    - camera_analyzer: 提供独立环境光分析
    - config: 全局调试开关
    - camera_controller: 摄像头重置函数

设计思路：
    - 每次运行前强制重置摄像头硬件，确保干净状态
    - 通过 set_debug(True) 启用所有模块的调试日志
    - 第 2、3 模式相互独立，可根据需要注释/取消注释

用法：
    在 REPL 中执行：
    import app
    app.main()
"""
# app.py
from photo_capturer import PhotoCapturer
import camera  # type: ignore
import camera_analyzer
from config import set_debug
from camera_controller import reset_camera  # 导入重置函数

# 启用调试日志（可改为 False 关闭所有模块调试输出）
set_debug(True)

def main():
    """
    主程序：演示三种拍照/分析模式。
    1. 仅拍照（不分析）
    2. 拍照并分析环境光（先分析后拍照）
    3. 独立环境光分析（不拍照）
    """
    # ---------- 关键：每次运行前强制重置摄像头硬件，确保干净状态 ----------
    print("\n[Main] Resetting camera hardware before start...")
    reset_camera()
    import time
    time.sleep_ms(200)

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

    # # ---------- 2. 拍照并分析 ----------
    # print("\n--- 2. 拍照并分析 ---")
    # capturer = PhotoCapturer(
    #     flash_pin=4,
    #     flash_on_value=1,
    #     sd_mount_point="/sd",
    #     camera_params={
    #         "framesize": camera.FRAME_XGA,
    #         "quality": 10,
    #         "flip": 1,
    #         "whitebalance": camera.WB_CLOUDY,
    #     }
    # )
    # saved_path, analysis = capturer.take_photo_with_analysis()
    # if saved_path:
    #     print("✅ Photo saved:", saved_path)
    #     if analysis:
    #         print("📊 Analysis:")
    #         print(f"  Average brightness: {analysis['average_brightness']:.1f}")
    #         print(f"  Dynamic range: {analysis['dynamic_range']}")
    #         print(f"  Center brightness: {analysis['center_brightness']:.1f}")
    # else:
    #     print("❌ Failed")
    # capturer.cleanup()

    # ---------- 3. 独立环境光分析 ----------
    print("\n--- 3. 独立环境光分析 ---")
    result = camera_analyzer.analyze_brightness_from_camera(
        framesize=camera.FRAME_XGA,
        step=2
    )
    if result:
        print(f"环境亮度: {result['average_brightness']:.1f}")
        print(f"动态范围: {result['dynamic_range']}")
        print(f"主体亮度: {result['center_brightness']:.1f}")
    else:
        print("分析失败")

if __name__ == "__main__":
    main()