"""
app.py - ESP32-CAM 简单拍照入口（调用 photo 包）
"""
from config import set_debug
from photo import simple_capture_with_downgrade
import camera

set_debug(True)

# 可选：自定义分辨率列表
PREFERRED = [
    camera.FRAME_QSXGA,
    camera.FRAME_UXGA,
    camera.FRAME_XGA,
    camera.FRAME_SVGA,
    camera.FRAME_VGA,
    camera.FRAME_QVGA,
]

def main():
    saved_path, w, h, req_w, req_h, framesize = simple_capture_with_downgrade(
        preferred_resolutions=PREFERRED
    )
    if saved_path:
        print("照片保存成功: {} (请求: {}x{}, 实际: {}x{})".format(
            saved_path, req_w, req_h, w, h))
    else:
        print("拍照失败")

if __name__ == "__main__":
    main()