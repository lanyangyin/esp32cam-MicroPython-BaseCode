# video/recorder_timestamp.py
"""
极速视频录制模块（按时间录制，文件名使用时间戳）
基于 recorder_time.py，将文件名改为时间戳（毫秒级）。
"""
import time
import gc
import uos
import camera
from sd_card import get_sd_card


class RecorderTimestamp:
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

    recorder = RecorderTimestamp(
        framesize=camera.FRAME_VGA,
        quality=10,
        save_dir="test_timestamp",
        xclk_freq=camera.XCLK_20MHz
    )

    frames, elapsed = recorder.start(duration_sec=10)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒, 帧速率 {:.2f} fps".format(
        frames, elapsed, frames/elapsed if elapsed > 0 else 0))
    recorder.close()


    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: timestamp, 时钟: 20000000
    # ================================================================================
    # 分辨率                  尺寸   帧数  耗时(s)  帧率(fps)
    # FRAME_240X240            240×240       77       5.03        15.30
    # FRAME_QCIF               176×144       72       5.00        14.39
    # FRAME_QQVGA              160×120       69       5.04        13.69
    # FRAME_HQVGA              240×176       68       5.01        13.56
    # FRAME_QVGA               320×240       68       5.06        13.44
    # FRAME_HVGA               480×320       60       5.03        11.93
    # FRAME_CIF                400×296       55       5.05        10.89
    # FRAME_VGA                640×480       47       5.09         9.24
    # FRAME_SVGA               800×600       35       5.05         6.93
    # FRAME_XGA               1024×768       21       5.01         4.19
    # FRAME_P_HD              720×1280       19       5.12         3.71
    # FRAME_HD                1280×720       16       5.36         2.99
    # FRAME_P_3MP             864×1536       11       5.07         2.17
    # FRAME_SXGA             1280×1024       11       5.27         2.09
    # FRAME_UXGA             1600×1200       10       5.13         1.95
    # FRAME_FHD              1920×1080       10       5.34         1.87
    # FRAME_QXGA             2048×1536        6       5.13         1.17
    # FRAME_96X96                96×96        0       8.00         0.00
    # ================================================================================
    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: timestamp, 时钟: 10000000
    # ================================================================================
    # 分辨率                  尺寸   帧数  耗时(s)  帧率(fps)
    # FRAME_HVGA               480×320       39       5.06         7.70
    # FRAME_96X96                96×96       38       5.03         7.56
    # FRAME_240X240            240×240       38       5.05         7.53
    # FRAME_QCIF               176×144       36       5.07         7.09
    # FRAME_HQVGA              240×176       34       5.07         6.70
    # FRAME_QQVGA              160×120       34       5.08         6.70
    # FRAME_QVGA               320×240       34       5.09         6.68
    # FRAME_VGA                640×480       34       5.10         6.67
    # FRAME_CIF                400×296       34       5.11         6.66
    # FRAME_SVGA               800×600       33       5.06         6.52
    # FRAME_XGA               1024×768       22       5.14         4.28
    # FRAME_P_HD              720×1280       19       5.09         3.73
    # FRAME_HD                1280×720       19       5.17         3.67
    # FRAME_SXGA             1280×1024       17       5.24         3.25
    # FRAME_P_3MP             864×1536       16       5.00         3.20
    # FRAME_FHD              1920×1080       11       5.27         2.09
    # FRAME_QXGA             2048×1536        8       5.08         1.58
    # FRAME_UXGA             1600×1200        8       5.08         1.57
    # ================================================================================