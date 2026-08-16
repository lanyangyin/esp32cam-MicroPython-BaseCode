# photo/plain_capture.py
"""
纯拍照模块（无闪光灯，无决策）

仅执行 JPEG 捕获，可选择保存到 SD 卡或仅返回数据。
不涉及任何亮度分析、闪光灯控制或自动决策。
遵循 KISS 原则：只做一件事——拍照（并可选保存）。

特点：
    - 不控制闪光灯（完全由调用者管理）
    - 不进行任何图像分析
    - 自动生成时间戳文件名或接受指定文件名（保存时）
    - 捕获后自动释放摄像头
    - 支持仅捕获数据不保存

典型用法：
    from photo import plain_capture

    # 保存到 SD 卡
    saved = plain_capture(framesize=camera.FRAME_XGA)
    if saved:
        print("照片已保存:", saved)

    # 仅获取 JPEG 数据，不保存
    jpeg_data = plain_capture(framesize=camera.FRAME_VGA, save_to_disk=False)
    if jpeg_data:
        print("捕获成功，大小:", len(jpeg_data))
"""
import time
import camera
from camera_driver import capture_image, reset_camera, CameraController
from sd_card import get_sd_card
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR


def plain_capture(framesize=camera.FRAME_XGA, quality=10, whitebalance=camera.WB_CLOUDY,
                  flip=1, mirror=0, filename=None, sd_mount_point="/sd",
                  save_to_disk=True):
    """
    纯 JPEG 捕获，可选择保存到 SD 卡或仅返回数据。

    参数：
        framesize (int): 分辨率常量，默认 FRAME_XGA。
        quality (int): JPEG 质量（10~63），默认 10。
        whitebalance (int): 白平衡模式，默认 WB_CLOUDY。
        flip (int): 上下翻转，1 翻转，0 不翻转。
        mirror (int): 左右镜像，1 镜像，0 不镜像。
        filename (str or None): 保存的文件名（绝对路径），若 None 则自动生成。
                                仅在 save_to_disk=True 时有效。
        sd_mount_point (str): SD 卡挂载点，默认 "/sd"。
        save_to_disk (bool): 是否保存到 SD 卡。True 返回文件路径，False 返回 JPEG 字节数据。

    返回：
        str or bytes or None:
            - 如果 save_to_disk=True 且成功，返回文件路径（str）。
            - 如果 save_to_disk=False 且捕获成功，返回 JPEG 数据（bytes）。
            - 如果失败，返回 None。
    """
    debug_log("纯拍照: framesize={}, save_to_disk={}".format(framesize, save_to_disk),
              level=LEVEL_INFO, module="PlainCapture")
    #
    # reset_camera()
    jpeg = capture_image(framesize=framesize, quality=quality,
                         format=camera.JPEG, flip=flip, mirror=mirror,
                         whitebalance=whitebalance)
    if jpeg is None:
        debug_log("JPEG 捕获失败", level=LEVEL_ERROR, module="PlainCapture")
        return None

    if not save_to_disk:
        debug_log("捕获成功，返回数据 ({} bytes)".format(len(jpeg)), level=LEVEL_INFO, module="PlainCapture")
        return jpeg

    # 保存到 SD 卡
    sd = get_sd_card(mount_point=sd_mount_point)
    if not sd.mounted:
        debug_log("SD 卡未挂载", level=LEVEL_ERROR, module="PlainCapture")
        return None

    if filename is None:
        filename = "/sd/plain_{}.jpg".format(int(time.time()))
    elif not filename.startswith(sd_mount_point):
        filename = sd_mount_point + "/" + filename.lstrip("/")

    saved = sd.save_file(jpeg, filename)
    if saved:
        debug_log("照片保存成功: {}".format(saved), level=LEVEL_INFO, module="PlainCapture")
        return saved
    else:
        debug_log("照片保存失败", level=LEVEL_ERROR, module="PlainCapture")
        return None


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug

    set_debug(True)

    print("=== 纯拍照模块测试 ===")
    sizelist = []
    for _ in range(10):

        # 测试1：保存到 SD 卡
        print("\n测试1: 保存到 SD 卡")
        saved = plain_capture(framesize=camera.FRAME_FHD)
        if saved:
            print("✅ 照片已保存:", saved)
        else:
            print("❌ 测试失败")

    #     # 测试2：仅捕获数据，不保存
    #     print("\n测试2: 仅捕获数据，不保存")
    #     jpeg_data = plain_capture(framesize=camera.FRAME_QCIF, save_to_disk=False)
    #     if jpeg_data:
    #         size = len(jpeg_data)
    #         sizelist.append(size)
    #         print("✅ 捕获成功，大小: {} bytes".format(size))
    #         # 可选：解析尺寸
    #         from utils import get_image_dimensions
    #
    #         w, h = get_image_dimensions(jpeg_data)
    #         print("   尺寸: {}x{}".format(w, h))
    #     else:
    #         print("❌ 测试失败")
    # for size in sizelist:
    #     print(size)
    print("\n测试完成")
    preferred_resolutions = [
        # camera.FRAME_96X96,  #                 96×96        0       8.00         0.00
        # camera.FRAME_QQVGA,  #               160×120       69       5.04        13.69
        camera.FRAME_QCIF,  #                176×144       72       5.00        14.39
        camera.FRAME_HQVGA,  #               240×176       68       5.01        13.56
        camera.FRAME_240X240,  #             240×240       77       5.03        15.30
        camera.FRAME_QVGA,  #                320×240       68       5.06        13.44
        camera.FRAME_CIF,  #                 400×296       55       5.05        10.89
        camera.FRAME_HVGA,  #                480×320       60       5.03        11.93
        camera.FRAME_VGA,  #                 640×480       47       5.09         9.24
        camera.FRAME_SVGA,  #                800×600       35       5.05         6.93
        camera.FRAME_P_HD,  #               720×1280       19       5.12         3.71
        camera.FRAME_P_3MP,  #              864×1536       11       5.07         2.17
        camera.FRAME_XGA,  #                1024×768       21       5.01         4.19
        camera.FRAME_HD,  #                 1280×720       16       5.36         2.99
        camera.FRAME_SXGA,  #              1280×1024       11       5.27         2.09
        camera.FRAME_UXGA,  #              1600×1200       10       5.13         1.95
        camera.FRAME_FHD,  #               1920×1080       10       5.34         1.87
        camera.FRAME_QXGA,  #              2048×1536        6       5.13         1.17
    ]