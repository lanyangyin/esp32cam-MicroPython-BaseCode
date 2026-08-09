"""
app.py - ESP32-CAM 主程序：智能拍照
"""
from config import set_debug
from photo import take_smart_photo
import camera, time

set_debug(True)

def main():
    start_time = time.ticks_ms()
    saved_path, w, h, brightness = take_smart_photo(
        analysis_framesize=camera.FRAME_HVGA,
        photo_framesize=camera.FRAME_QXGA,
        retry_analysis_limit=6,
        retry_capture_limit=6,
        decision_mode="quick"
    )
    if saved_path:
        elapsed = (time.ticks_ms() - start_time) / 1000.0
        print("照片保存成功: {}, 尺寸: {}x{}, 亮度: {:.1f}， 时间: {}".format(saved_path, w, h, brightness['average_brightness'], elapsed))
    else:
        print("拍照失败")

if __name__ == "__main__":
    main()