# video/fast_recorder.py
"""
极速视频录制模块 - 无日志、无额外检查，专注于最高帧率。
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
                 keep_camera_open=True):
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
                        xclk_freq=camera.XCLK_10MHz)
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
        framesize=camera.FRAME_HVGA,
        quality=10,
        use_flash=False,
        keep_camera_open=True
    )

    # 录制 5 秒
    frames, elapsed = recorder.start(duration_sec=5)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒".format(frames, elapsed))

    # 释放摄像头
    recorder.close()


    # ============================================================
    # 基准测试结果汇总
    # ============================================================
    # 分辨率         帧数  耗时(s) 帧率(fps)
    # FRAME_P_3MP           14       5.02       2.79
    # FRAME_SVGA            34       5.13       6.63
    # FRAME_QXGA            13       5.07       2.56
    # FRAME_QCIF            36       5.07       7.10
    # FRAME_QVGA            34       5.10       6.67
    # FRAME_HVGA            39       5.08       7.68
    # FRAME_CIF             34       5.10       6.66
    # FRAME_SXGA            18       5.09       3.53
    # FRAME_HD              21       5.18       4.05
    # FRAME_QQVGA           34       5.09       6.69
    # FRAME_VGA             34       5.10       6.67
    # FRAME_96X96            0       8.02       0.00
    # FRAME_HQVGA           34       5.08       6.70
    # FRAME_XGA             17       5.23       3.25
    # FRAME_240X240         38       5.03       7.55
    # FRAME_FHD             13       5.18       2.51
    # FRAME_P_HD            17       5.03       3.38
    # FRAME_UXGA            13       5.13       2.54
    # ============================================================