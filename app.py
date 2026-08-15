"""
app.py - ESP32-CAM 主程序：循环检测 TXD 短接触发拍照
"""
import time
from machine import Pin
from config import set_debug
from photo import take_smart_photo
import camera

set_debug(True)

# 触发引脚：GPIO 1（TXD），低电平有效（短接到 GND）
# 注意：GPIO 1 同时是 UART0 TX，若需保持串口正常，建议改用其他空闲引脚（如 GPIO 14、15）
TRIGGER_PIN = 1

def main():
    # # 初始化引脚为输入，启用内部上拉
    # trigger = Pin(TRIGGER_PIN, Pin.IN, Pin.PULL_UP)
    # print("等待触发... 将 TXD 与 GND 短接即可拍照（按 Ctrl+C 退出）")
    #
    # while True:
    #     # 检测引脚电平
    #     if trigger.value() == 0:  # 低电平表示短接
    print("触发！开始拍照...")
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
    # 拍照后延时避免重复触发（防抖）
    time.sleep_ms(500)
        # else:
        #     # 每隔 1 秒检测一次
        #     time.sleep(1)

if __name__ == "__main__":
    main()