# video/recorder_frames.py
"""
极速视频录制模块（按帧数录制，单线程版本）
指定总帧数，主循环每50帧执行一次内存回收。
录制结束条件：达到目标帧数 或 手动停止。
"""
import time
import gc
import uos
import camera
from sd_card import get_sd_card


class RecorderFrames:
    """
    按帧数录制的极速录制器（无闪光灯，单线程）
    主循环仅捕获和保存，每50帧执行一次 gc.collect()。
    """

    def __init__(self, framesize=camera.FRAME_VGA, quality=10,
                 sd_mount_point="/sd", save_dir="video",
                 xclk_freq=camera.XCLK_10MHz):
        """
        参数：
            framesize: 捕获分辨率
            quality: JPEG 质量 (10-63)
            sd_mount_point: SD 卡挂载点
            save_dir: 保存目录名称
            xclk_freq: 摄像头时钟频率
        """
        self.framesize = framesize
        self.quality = quality
        self.sd_mount_point = sd_mount_point
        self.save_dir = save_dir
        self.xclk_freq = xclk_freq
        self._cam_initialized = False
        self._recording = False

        self.sd = get_sd_card(mount_point=sd_mount_point)
        if not self.sd.mounted:
            raise RuntimeError("SD card not mounted")

        self.full_dir = self._create_save_dir()

    def _create_save_dir(self):
        """创建带序号的保存目录"""
        dir_name = self.save_dir
        counter = 1
        while True:
            full_path = "{}/{}".format(self.sd_mount_point, dir_name)
            try:
                uos.mkdir(full_path)
                return full_path
            except OSError:
                dir_name = "{}_{}".format(self.save_dir, counter)
                counter += 1
                if counter > 100:
                    raise RuntimeError("无法创建目录，重名太多")

    def _init_camera(self):
        """初始化摄像头"""
        if not self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            camera.init(0,
                        format=camera.JPEG,
                        fb_location=camera.PSRAM,
                        framesize=self.framesize,
                        xclk_freq=self.xclk_freq)
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
        """释放摄像头"""
        if self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            self._cam_initialized = False

    def start(self, total_frames):
        """
        开始录制指定帧数。
        参数：
            total_frames: 要录制的总帧数
        返回：
            (实际帧数, 实际耗时秒数)
        """
        if self._recording:
            return
        if total_frames <= 0:
            raise ValueError("total_frames 必须大于 0")

        # 1. 释放摄像头并初始化
        self._deinit_camera()
        time.sleep_ms(200)
        self._init_camera()

        self._recording = True
        frame_count = 0
        start_time = time.ticks_ms()

        try:
            while self._recording and frame_count < total_frames:
                buf = camera.capture()
                if buf is not None and buf is not False:
                    filename = "{}/f_{:06d}.jpg".format(self.full_dir, frame_count)
                    try:
                        with open(filename, "wb") as f:
                            f.write(buf)
                        frame_count += 1
                    except:
                        pass

                # 每 50 帧回收一次内存
                if frame_count % 50 == 0:
                    gc.collect()

        except KeyboardInterrupt:
            pass
        finally:
            self._recording = False
            self._deinit_camera()

        elapsed = (time.ticks_ms() - start_time) / 1000.0
        return frame_count, elapsed

    def stop(self):
        """停止录制"""
        self._recording = False

    def close(self):
        """释放摄像头资源"""
        self._deinit_camera()


if __name__ == "__main__":
    import camera

    recorder = RecorderFrames(
        framesize=camera.FRAME_CIF,
        quality=10,
        save_dir="test_frames_single",
        xclk_freq=camera.XCLK_20MHz
    )

    total = 100  # 录制100帧
    frames, elapsed = recorder.start(total_frames=total)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒, 帧速率 {:.2f} fps".format(frames, elapsed, frames/elapsed if elapsed > 0 else 0))
    recorder.close()