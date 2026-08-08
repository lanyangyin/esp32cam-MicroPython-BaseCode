# video/recorder.py
"""
视频录制（快速连拍）模块
以最大速度连续捕获 JPEG 图像并保存为序号文件。
支持按帧数或按持续时间录制。
"""
import time
import gc
import camera
from config import debug_log, LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR, LEVEL_DEBUG
from camera_driver import capture_image
from sd_card import get_sd_card
from flash import get_flash


class VideoRecorder:
    def __init__(self, framesize=camera.FRAME_XGA, quality=10,
                 flash_pin=4, flash_on_value=1,
                 sd_mount_point="/sd", use_flash=False):
        """
        参数：
            framesize: 捕获分辨率
            quality: JPEG 质量
            flash_pin: 闪光灯引脚（连拍时通常关闭，设为 None 禁用）
            sd_mount_point: SD卡挂载点
            use_flash: 是否开启闪光灯（连拍建议关闭，否则会严重降低帧率）
        """
        self.framesize = framesize
        self.quality = quality
        self.flash_pin = flash_pin
        self.flash_on_value = flash_on_value
        self.sd_mount_point = sd_mount_point
        self.use_flash = use_flash
        self._recording = False
        self.frame_count = 0

        # SD 卡实例
        self.sd = get_sd_card(mount_point=sd_mount_point)
        if not self.sd.mounted:
            raise RuntimeError("SD card not mounted")

        # 闪光灯实例（如果启用）
        self.flash = None
        if use_flash and flash_pin is not None:
            self.flash = get_flash(pin=flash_pin, on_value=flash_on_value)

    def start(self, total_frames=None, duration_sec=None):
        """
        开始录制（以最快速度捕获）。
        参数：
            total_frames: 总帧数（与 duration_sec 二选一）
            duration_sec: 持续秒数
        返回：
            (实际捕获的帧数, 实际耗时秒数)
        """
        if self._recording:
            debug_log("录制已在运行", level=LEVEL_WARNING, module="Recorder")
            return

        if total_frames is None and duration_sec is None:
            raise ValueError("必须指定 total_frames 或 duration_sec")

        self.frame_count = 0
        self._recording = True

        # 计算结束条件
        if duration_sec is not None:
            end_time = time.ticks_add(time.ticks_ms(), int(duration_sec * 1000))
            target_frames = None
            debug_log("开始录制，时长: {} 秒".format(duration_sec), level=LEVEL_INFO, module="Recorder")
        else:
            end_time = None
            target_frames = total_frames
            debug_log("开始录制，目标帧数: {}".format(total_frames), level=LEVEL_INFO, module="Recorder")

        start_time = time.ticks_ms()
        w, h = self._get_resolution()
        debug_log("分辨率: {}x{}".format(w, h), level=LEVEL_INFO, module="Recorder")

        try:
            while self._recording:
                # 检查是否达到帧数限制
                if target_frames is not None and self.frame_count >= target_frames:
                    break
                # 检查是否达到时间限制
                if end_time is not None and time.ticks_ms() >= end_time:
                    break

                self._capture_and_save()
                self.frame_count += 1

                # 每 10 帧回收一次内存
                if self.frame_count % 10 == 0:
                    gc.collect()

        except KeyboardInterrupt:
            debug_log("手动停止录制", level=LEVEL_WARNING, module="Recorder")
        finally:
            self._recording = False
            elapsed = (time.ticks_ms() - start_time) / 1000.0
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            debug_log("录制结束，共捕获 {} 帧，耗时 {:.2f} 秒，平均帧率: {:.1f} fps".format(
                self.frame_count, elapsed, fps), level=LEVEL_INFO, module="Recorder")

        return self.frame_count, elapsed

    def stop(self):
        """停止录制"""
        self._recording = False

    def _capture_and_save(self):
        """捕获一帧并保存（尽可能快）"""
        # 闪光灯控制（如果需要）
        flash_on = self.flash and self.use_flash
        if flash_on:
            self.flash.on()
            time.sleep_ms(50)  # 曝光稳定（仅当使用闪光灯时）

        # 捕获
        jpeg = capture_image(
            framesize=self.framesize,
            quality=self.quality,
            format=camera.JPEG,
            flip=1,
            whitebalance=camera.WB_CLOUDY
        )

        if flash_on:
            self.flash.off()

        if jpeg is None:
            debug_log("捕获失败，跳过此帧", level=LEVEL_WARNING, module="Recorder")
            return

        # 保存为序号文件
        filename = "{}/frame_{:06d}.jpg".format(self.sd_mount_point, self.frame_count)
        if self.sd.save_file(jpeg, filename):
            debug_log("帧 {} 保存成功 ({} bytes)".format(self.frame_count, len(jpeg)), level=LEVEL_DEBUG, module="Recorder")
        else:
            debug_log("帧 {} 保存失败".format(self.frame_count), level=LEVEL_ERROR, module="Recorder")

    def _get_resolution(self):
        from camera_driver import CameraController
        return CameraController.get_resolution(self.framesize) or (0, 0)


if __name__ == "__main__":
    import camera

    recorder = VideoRecorder(
        framesize=camera.FRAME_VGA,
        quality=10,
        use_flash=False
    )
    # 录制 10 秒（最快速度）
    frames, elapsed = recorder.start(duration_sec=10)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒".format(frames, elapsed))