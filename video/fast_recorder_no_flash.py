# video/fast_recorder_no_flash.py
"""
极速视频录制模块（无闪光灯、无帧数计数）
仅支持按时间录制，使用内部计数器统计帧数。
初始化前彻底释放摄像头，每14秒回收一次内存。
"""
import time
import gc
import uos
import camera
from sd_card import get_sd_card


class FastRecorderNoFlash:
    """
    极速录制器（无闪光灯版本）
    以最快速度连续捕获 JPEG 并保存到指定目录。
    目录不存在则创建，若已存在则自动添加序号 (_1, _2, ...)
    """

    def __init__(self, framesize=camera.FRAME_VGA, quality=10,
                 sd_mount_point="/sd", save_dir="video",
                 xclk_freq=camera.XCLK_10MHz):
        """
        参数：
            framesize: 捕获分辨率
            quality: JPEG 质量 (10-63)
            sd_mount_point: SD 卡挂载点（必须已挂载）
            save_dir: 保存目录名称（在挂载点下）
            xclk_freq: 摄像头时钟频率 (camera.XCLK_10MHz 或 camera.XCLK_20MHz)
        """
        self.framesize = framesize
        self.quality = quality
        self.sd_mount_point = sd_mount_point
        self.save_dir = save_dir
        self.xclk_freq = xclk_freq
        self._cam_initialized = False
        self._recording = False

        # 确保 SD 卡已挂载
        self.sd = get_sd_card(mount_point=sd_mount_point)
        if not self.sd.mounted:
            raise RuntimeError("SD card not mounted")

        # 创建保存目录（自动处理重名）
        self.full_dir = self._create_save_dir()

    def _create_save_dir(self):
        """创建保存目录，若已存在则自动添加尾号"""
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
        """彻底释放摄像头"""
        if self._cam_initialized:
            try:
                camera.deinit()
            except:
                pass
            self._cam_initialized = False

    def start(self, duration_sec):
        """
        开始录制（以最快速度）。
        参数：
            duration_sec: 持续秒数
        返回：
            (实际帧数, 实际耗时秒数)
        """
        if self._recording:
            return

        if duration_sec <= 0:
            raise ValueError("duration_sec 必须大于 0")

        # 1. 无条件彻底释放摄像头（确保干净状态）
        self._deinit_camera()
        time.sleep_ms(200)  # 给硬件足够时间复位

        # 2. 初始化摄像头
        self._init_camera()

        self._recording = True
        frame_count = 0
        start_time = time.ticks_ms()
        end_time = time.ticks_add(start_time, int(duration_sec * 1000))

        # 内存回收计时（14秒间隔）
        last_gc_time = start_time
        GC_INTERVAL = 14000  # 14 秒

        try:
            while self._recording:
                if time.ticks_ms() >= end_time:
                    break

                buf = camera.capture()

                if buf is not None and buf is not False:
                    filename = "{}/f_{:06d}.jpg".format(self.full_dir, frame_count)
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
            # 彻底释放摄像头
            self._deinit_camera()

        elapsed = (time.ticks_ms() - start_time) / 1000.0

        # 直接使用计数器返回帧数
        return frame_count, elapsed

    def stop(self):
        """停止录制（外部调用）"""
        self._recording = False

    def close(self):
        """释放摄像头资源"""
        self._deinit_camera()


if __name__ == "__main__":
    import camera

    recorder = FastRecorderNoFlash(
        framesize=camera.FRAME_VGA,
        quality=10,
        save_dir="test",
        xclk_freq=camera.XCLK_20MHz
    )

    frames, elapsed = recorder.start(duration_sec=10)
    print("录制完成: {} 帧, 耗时 {:.2f} 秒, 帧速率{:.2f}/s".format(frames, elapsed, frames/elapsed))
    recorder.close()