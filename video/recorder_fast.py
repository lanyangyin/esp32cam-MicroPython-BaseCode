# video/recorder_fast.py
"""
极速视频录制模块 - 无日志、无额外检查，专注于最高帧率。
支持闪光灯和保持摄像头常开。
直接使用 camera 模块，保持摄像头常开以避免重复初始化。
"""
import time
import gc
import camera
from machine import Pin
from sd_card import get_sd_card


class FastRecorder:
    """
    极速录制器，以最快速度连续捕获 JPEG 并保存。
    默认保持摄像头常开，不输出任何日志，不检查图片尺寸。
    """

    def __init__(self, framesize=camera.FRAME_VGA, quality=10,
                 flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", use_flash=False,
                 keep_camera_open=True,
                 xclk_freq=camera.XCLK_10MHz):   # 新增
        """
        参数：
            framesize: 捕获分辨率
            quality: JPEG 质量 (10-63)
            flash_pin: 闪光灯 GPIO 引脚
            flash_on_value: 点亮电平 (1 或 0)
            sd_mount_point: SD 卡挂载点
            use_flash: 是否启用闪光灯（会降低帧率）
            keep_camera_open: 是否保持摄像头初始化 (True 可提高帧率)
        """
        self.framesize = framesize
        self.quality = quality
        self.sd_mount_point = sd_mount_point
        self.use_flash = use_flash
        self.keep_camera_open = keep_camera_open
        self.xclk_freq = xclk_freq                # 存储

        # SD 卡
        self.sd = get_sd_card(mount_point=sd_mount_point)
        if not self.sd.mounted:
            raise RuntimeError("SD card not mounted")

        # 闪光灯 (GPIO)
        self.flash = None
        if use_flash and flash_pin is not None:
            self.flash = Pin(flash_pin, Pin.OUT)
            # 初始关闭
            self.flash.value(0 if flash_on_value == 0 else 1 - flash_on_value)
            self.flash_on_value = flash_on_value

        self._cam_initialized = False
        self._recording = False
        self.frame_count = 0

    def _init_camera(self):
        """初始化摄像头（若未初始化）"""
        if not self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            camera.init(0,
                        format=camera.JPEG,
                        fb_location=camera.PSRAM,
                        framesize=self.framesize,
                        xclk_freq=self.xclk_freq)   # 使用存储的值
            camera.flip(1)
            camera.mirror(0)
            camera.saturation(0)
            camera.brightness(0)
            camera.contrast(0)
            camera.whitebalance(camera.WB_CLOUDY)
            camera.speffect(camera.EFFECT_NONE)
            camera.quality(self.quality)
            self._cam_initialized = True

    def _deinit_camera(self):
        """释放摄像头（仅在 keep_camera_open=False 时调用）"""
        if self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            self._cam_initialized = False

    def start(self, total_frames=None, duration_sec=None):
        """
        开始录制（以最快速度）。
        参数：
            total_frames: 总帧数
            duration_sec: 持续秒数 (与 total_frames 二选一)
        返回：
            (实际帧数, 实际耗时秒数)
        """
        if self._recording:
            return

        if total_frames is None and duration_sec is None:
            raise ValueError("必须指定 total_frames 或 duration_sec")

        # 初始化摄像头
        self._init_camera()

        self._recording = True
        self.frame_count = 0

        start_time = time.ticks_ms()
        if duration_sec is not None:
            end_time = time.ticks_add(start_time, int(duration_sec * 1000))
            target_frames = None
        else:
            end_time = None
            target_frames = total_frames

        try:
            while self._recording:
                # 检查终止条件
                if target_frames is not None and self.frame_count >= target_frames:
                    break
                if end_time is not None and time.ticks_ms() >= end_time:
                    break

                # 闪光灯 (若启用)
                if self.use_flash and self.flash:
                    self.flash.value(self.flash_on_value)
                    time.sleep_ms(30)  # 曝光稳定

                # 捕获 JPEG
                buf = camera.capture()

                if self.use_flash and self.flash:
                    self.flash.value(1 - self.flash_on_value)

                # 若捕获成功，立即保存 (无任何检查)
                if buf is not None and buf is not False:
                    filename = "{}/f_{:06d}.jpg".format(self.sd_mount_point, self.frame_count)
                    try:
                        with open(filename, "wb") as f:
                            f.write(buf)
                        self.frame_count += 1
                    except:
                        pass  # 写入失败则跳过此帧

                # 每 100 帧回收一次内存
                if self.frame_count % 100 == 0:
                    gc.collect()

        except KeyboardInterrupt:
            pass
        finally:
            self._recording = False
            if not self.keep_camera_open:
                self._deinit_camera()

        elapsed = (time.ticks_ms() - start_time) / 1000.0
        return self.frame_count, elapsed

    def stop(self):
        """停止录制"""
        self._recording = False

    def close(self):
        """释放摄像头资源"""
        self._deinit_camera()


if __name__ == "__main__":
    import camera

    recorder = FastRecorder(
        framesize=camera.FRAME_SVGA,
        quality=10,
        use_flash=False,
        keep_camera_open=True
    )

    # 录制 5 秒
    frames, elapsed = recorder.start(duration_sec=10)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒".format(frames, elapsed))

    # 释放摄像头
    recorder.close()


    # video/benchmark.py
    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: fast, 时钟: 20000000
    # ================================================================================
    # 分辨率                    尺寸         帧数      耗时(s)       帧率(fps)
    # FRAME_240X240            240×240       77       5.00        15.39
    # FRAME_QCIF               176×144       73       5.04        14.50
    # FRAME_QQVGA              160×120       69       5.04        13.70
    # FRAME_HQVGA              240×176       69       5.05        13.66
    # FRAME_QVGA               320×240       68       5.05        13.45
    # FRAME_HVGA               480×320       56       5.01        11.18
    # FRAME_CIF                400×296       54       5.01        10.77
    # FRAME_VGA                640×480       43       5.06         8.50
    # FRAME_SVGA               800×600       31       5.04         6.15
    # FRAME_XGA               1024×768       22       5.17         4.26
    # FRAME_P_HD              720×1280       20       5.08         3.94
    # FRAME_HD                1280×720       14       5.23         2.68
    # FRAME_SXGA             1280×1024       11       5.08         2.17
    # FRAME_UXGA             1600×1200       10       5.22         1.92
    # FRAME_FHD              1920×1080       10       5.53         1.81
    # FRAME_P_3MP             864×1536        8       5.22         1.53
    # FRAME_QXGA             2048×1536        7       5.31         1.32
    # FRAME_96X96                96×96        0       8.03         0.00
    # ================================================================================
    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: fast, 时钟: 10000000
    # ================================================================================
    # 分辨率                    尺寸         帧数      耗时(s)       帧率(fps)
    # FRAME_HVGA               480×320       39       5.04         7.74
    # FRAME_240X240            240×240       38       5.03         7.55
    # FRAME_QCIF               176×144       36       5.07         7.11
    # FRAME_HQVGA              240×176       34       5.07         6.70
    # FRAME_QQVGA              160×120       34       5.08         6.70
    # FRAME_QVGA               320×240       34       5.10         6.67
    # FRAME_CIF                400×296       34       5.11         6.66
    # FRAME_VGA                640×480       34       5.14         6.61
    # FRAME_XGA               1024×768       21       5.01         4.19
    # FRAME_HD                1280×720       21       5.08         4.13
    # FRAME_SVGA               800×600       19       5.01         3.79
    # FRAME_UXGA             1600×1200       17       5.17         3.29
    # FRAME_SXGA             1280×1024       17       5.29         3.22
    # FRAME_FHD              1920×1080       16       5.26         3.04
    # FRAME_P_3MP             864×1536       14       5.23         2.68
    # FRAME_QXGA             2048×1536       13       5.09         2.56
    # FRAME_P_HD              720×1280       13       5.22         2.49
    # FRAME_96X96                96×96        0       8.03         0.00
    # ================================================================================