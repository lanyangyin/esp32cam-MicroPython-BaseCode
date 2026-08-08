"""
app.py - ESP32-CAM 主程序：智能拍照
"""
from config import set_debug
from photo import smart_capture_with_analysis
import camera

set_debug(True)

def main():
    saved_path, w, h, brightness = smart_capture_with_analysis(
        analysis_framesize=camera.FRAME_QVGA,
        photo_framesize=camera.FRAME_XGA,
        retry_analysis_limit=6,
        retry_capture_limit=6
    )
    if saved_path:
        print("照片保存成功: {}, 尺寸: {}x{}, 亮度: {:.1f}".format(
            saved_path, w, h, brightness['average_brightness']))
    else:
        print("拍照失败")

if __name__ == "__main__":
    main()