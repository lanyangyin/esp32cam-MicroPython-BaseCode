# video/fast_recorder_timestamp.py
"""
极速视频录制模块（按时间录制，文件名使用时间戳）
基于 fast_recorder_no_flash.py，将文件名改为时间戳（毫秒级）。
"""
import time
import gc
import uos
import camera
from sd_card import get_sd_card


class FastRecorderTimestamp:
    """
    按时间录制的极速录制器（无闪光灯）
    文件名使用 time.ticks_ms() 作为时间戳，确保唯一性。
    """

    def __init__(self, framesize=camera.FRAME_VGA, quality=10,
                 sd_mount_point="/sd", save_dir="video",
                 xclk_freq=camera.XCLK_10MHz):
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
        if self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            self._cam_initialized = False

    def start(self, duration_sec):
        if self._recording:
            return

        if duration_sec <= 0:
            raise ValueError("duration_sec 必须大于 0")

        self._deinit_camera()
        time.sleep_ms(200)
        self._init_camera()

        self._recording = True
        frame_count = 0
        start_time = time.ticks_ms()
        end_time = time.ticks_add(start_time, int(duration_sec * 1000))

        last_gc_time = start_time
        GC_INTERVAL = 14000  # 14 秒

        try:
            while self._recording:
                if time.ticks_ms() >= end_time:
                    break

                buf = camera.capture()

                if buf is not None and buf is not False:
                    # 使用时间戳（毫秒）作为文件名
                    timestamp = time.ticks_ms()
                    filename = "{}/{}.jpg".format(self.full_dir, timestamp)
                    try:
                        with open(filename, "wb") as f:
                            f.write(buf)
                        frame_count += 1
                    except:
                        pass

                now = time.ticks_ms()
                if time.ticks_diff(now, last_gc_time) > GC_INTERVAL:
                    gc.collect()
                    last_gc_time = now

        except KeyboardInterrupt:
            pass
        finally:
            self._recording = False
            self._deinit_camera()

        elapsed = (time.ticks_ms() - start_time) / 1000.0
        return frame_count, elapsed

    def stop(self):
        self._recording = False

    def close(self):
        self._deinit_camera()


if __name__ == "__main__":
    import camera

    recorder = FastRecorderTimestamp(
        framesize=camera.FRAME_VGA,
        quality=10,
        save_dir="test_timestamp",
        xclk_freq=camera.XCLK_20MHz
    )

    frames, elapsed = recorder.start(duration_sec=10)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒, 帧速率 {:.2f} fps".format(
        frames, elapsed, frames/elapsed if elapsed > 0 else 0))
    recorder.close()