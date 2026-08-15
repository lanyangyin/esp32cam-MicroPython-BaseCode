"""
app.py - ESP32-CAM 主程序：循环检测 TXD 短接触发拍照
"""
import time
from machine import Pin
from config import set_debug
from config.camera_model import CAMERA_MODEL
from photo import take_smart_photo
import camera

set_debug(True)

def main():
    print("当前摄像头型号:", CAMERA_MODEL)
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

if __name__ == "__main__":
    main()