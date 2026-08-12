"""
app.py - ESP32-CAM 主程序：循环检测 GPIO 0 触发拍照，连续三次触发则录像一分钟
"""
import time
from machine import Pin
from config import set_debug
from photo import take_smart_photo
from video import RecorderTimestamp   # 使用时间戳命名的录制器
import camera

set_debug(True)

# 触发引脚：GPIO 0，低电平有效（短接到 GND）
# 注意：GPIO 0 在启动时如果被拉低会进入下载模式，请确保启动时按钮未被按下
TRIGGER_PIN = 0

# 录像参数
VIDEO_DURATION = 60  # 秒
VIDEO_FRAMESIZE = camera.FRAME_VGA
VIDEO_QUALITY = 10
VIDEO_XCLK = camera.XCLK_20MHz

def main():
    # 启动延时，避免启动时 GPIO 0 被误拉低进入下载模式
    print("系统启动中... 请等待 2 秒")
    time.sleep(2)

    # 初始化引脚为输入，启用内部上拉
    trigger = Pin(TRIGGER_PIN, Pin.IN, Pin.PULL_UP)
    print("等待触发... 将 GPIO 0 与 GND 短接即可拍照（按 Ctrl+C 退出）")
    print("连续触发 3 次将自动录像一分钟")

    trigger_count = 0   # 连续触发计数

    while True:
        if trigger.value() == 0:  # 低电平表示短接
            # 简单去抖：等待 50ms 后再次检测
            time.sleep_ms(50)
            if trigger.value() == 0:
                trigger_count += 1
                print(f"触发！开始拍照... (连续第 {trigger_count} 次)")

                # 执行智能拍照
                start_time = time.ticks_ms()
                saved_path, w, h, brightness = take_smart_photo(
                    analysis_framesize=camera.FRAME_HVGA,
                    photo_framesize=camera.FRAME_QXGA,
                    retry_analysis_limit=6,
                    retry_capture_limit=6,
                    decision_mode="quick"
                )
                elapsed = (time.ticks_ms() - start_time) / 1000.0
                if saved_path:
                    print("照片保存成功: {}, 尺寸: {}x{}, 亮度: {:.1f}，耗时: {:.2f}s".format(
                        saved_path, w, h, brightness['average_brightness'], elapsed))
                else:
                    print("拍照失败")

                # 检查是否连续触发达到 3 次
                if trigger_count >= 3:
                    print("连续触发 3 次！开始录像一分钟...")
                    # 创建录制器
                    recorder = RecorderTimestamp(
                        framesize=VIDEO_FRAMESIZE,
                        quality=VIDEO_QUALITY,
                        save_dir="video_clip",
                        xclk_freq=VIDEO_XCLK
                    )
                    frames, elapsed = recorder.start(duration_sec=VIDEO_DURATION)
                    recorder.close()
                    print(f"录像完成: {frames} 帧, 耗时 {elapsed:.2f} 秒")
                    # 重置计数器
                    trigger_count = 0

                # 防重复触发
                time.sleep_ms(500)
        else:
            # 未触发，重置计数器
            if trigger_count != 0:
                print("触发中断，重置计数")
                trigger_count = 0
            # 每隔 100ms 检测一次（提高响应）
            time.sleep_ms(100)

if __name__ == "__main__":
    main()