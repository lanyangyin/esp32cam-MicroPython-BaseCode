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

from indicator import get_indicator
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

        indicator = get_indicator()
        indicator.on()
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
            indicator.off()
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


    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: frames, 时钟: 20000000
    # ================================================================================
    # 分辨率                    尺寸         帧数      耗时(s)       帧率(fps)
    # FRAME_240X240            240×240      100       6.51        15.37
    # FRAME_HVGA               480×320      100       6.74        14.84
    # FRAME_HQVGA              240×176      100       7.31        13.67
    # FRAME_QVGA               320×240      100       7.33        13.64
    # FRAME_CIF                400×296      100       9.10        10.99
    # FRAME_VGA                640×480      100      10.22         9.78
    # FRAME_SVGA               800×600      100      16.14         6.20
    # FRAME_XGA               1024×768      100      22.52         4.44
    # FRAME_P_HD              720×1280      100      27.56         3.63
    # FRAME_HD                1280×720      100      27.65         3.62
    # FRAME_P_3MP             864×1536      100      40.35         2.48
    # FRAME_SXGA             1280×1024      100      41.72         2.40
    # FRAME_UXGA             1600×1200      100      56.42         1.77
    # FRAME_FHD              1920×1080      100      61.79         1.62
    # FRAME_QXGA             2048×1536      100      83.06         1.20
    # ================================================================================
    # ================================================================================
    # 基准测试结果汇总 (按帧率降序) - 录制器: frames, 时钟: 10000000
    # ================================================================================
    # 分辨率                    尺寸         帧数      耗时(s)       帧率(fps)
    # FRAME_HVGA               480×320       50       6.47         7.73
    # FRAME_240X240            240×240       50       6.64         7.53
    # FRAME_HQVGA              240×176       50       7.42         6.74
    # FRAME_CIF                400×296       50       7.44         6.72
    # FRAME_QVGA               320×240       50       7.45         6.72
    # FRAME_SVGA               800×600       50       7.51         6.66
    # FRAME_VGA                640×480       50       8.56         5.84
    # FRAME_XGA               1024×768       50       9.82         5.09
    # FRAME_HD                1280×720       50      13.77         3.63
    # FRAME_P_3MP             864×1536       50      14.07         3.55
    # FRAME_SXGA             1280×1024       50      14.74         3.39
    # FRAME_P_HD              720×1280       50      14.74         3.39
    # FRAME_QXGA             2048×1536       50      20.43         2.45
    # FRAME_UXGA             1600×1200       50      22.40         2.23
    # FRAME_FHD              1920×1080       50      22.90         2.18
    # ================================================================================