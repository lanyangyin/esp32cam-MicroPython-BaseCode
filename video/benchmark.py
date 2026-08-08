# video/benchmark.py
"""
视频录制帧率基准测试
支持选择不同的录制器类型和 xclk_freq。
测试从 FRAME_96X96 到 FRAME_QXGA 的各个分辨率，记录平均帧率。
"""
import time
import gc
import uos
import camera
from .recorder_fast import FastRecorder
from .recorder_time import RecorderTime
from .recorder_timestamp import RecorderTimestamp
from .recorder import Recorder
from camera_driver.resolutions import get_resolution

# 要测试的分辨率（名称和常量）
RESOLUTIONS = [
    ("FRAME_96X96", camera.FRAME_96X96),
    ("FRAME_QQVGA", camera.FRAME_QQVGA),
    ("FRAME_QCIF", camera.FRAME_QCIF),
    ("FRAME_HQVGA", camera.FRAME_HQVGA),
    ("FRAME_240X240", camera.FRAME_240X240),
    ("FRAME_QVGA", camera.FRAME_QVGA),
    ("FRAME_CIF", camera.FRAME_CIF),
    ("FRAME_HVGA", camera.FRAME_HVGA),
    ("FRAME_VGA", camera.FRAME_VGA),
    ("FRAME_SVGA", camera.FRAME_SVGA),
    ("FRAME_XGA", camera.FRAME_XGA),
    ("FRAME_HD", camera.FRAME_HD),
    ("FRAME_SXGA", camera.FRAME_SXGA),
    ("FRAME_UXGA", camera.FRAME_UXGA),
    ("FRAME_FHD", camera.FRAME_FHD),
    ("FRAME_P_HD", camera.FRAME_P_HD),
    ("FRAME_P_3MP", camera.FRAME_P_3MP),
    ("FRAME_QXGA", camera.FRAME_QXGA),
]

# 每个分辨率录制时长（秒）
DEFAULT_DURATION = 5

def run_benchmark(duration=DEFAULT_DURATION, recorder_type='fast', xclk_freq=camera.XCLK_10MHz):
    """
    执行帧率基准测试。

    参数：
        duration (int): 每个分辨率的录制秒数
        recorder_type (str): 录制器类型，可选 'fast', 'time', 'timestamp', 'recorder'
            - 'fast'      : 使用 FastRecorder（极速，可保持摄像头常开，无日志）
            - 'time'      : 使用 RecorderTime（按时间录制，14秒GC，序号文件名）
            - 'timestamp' : 使用 RecorderTimestamp（按时间录制，14秒GC，时间戳文件名）
            - 'recorder'  : 使用 Recorder（通用录制器，有日志和闪光灯支持）
        xclk_freq (int): 摄像头时钟频率，仅在 'time' 和 'timestamp' 模式下有效
                         支持 camera.XCLK_10MHz 或 camera.XCLK_20MHz

    返回：
        dict: {分辨率名称: (帧数, 耗时秒, 帧率)}
    """
    print("\n开始帧率基准测试...")
    print("录制器类型: {}, 时钟频率: {}, 每个分辨率录制 {} 秒".format(
        recorder_type, xclk_freq, duration))

    # 选择录制器类
    if recorder_type == 'fast':
        RecorderCls = FastRecorder
        extra_args = {}  # FastRecorder 不支持 xclk_freq
        save_dir = None  # 不使用子目录
    elif recorder_type == 'time':
        RecorderCls = RecorderTime
        extra_args = {'xclk_freq': xclk_freq}
        save_dir = "time"
    elif recorder_type == 'timestamp':
        RecorderCls = RecorderTimestamp
        extra_args = {'xclk_freq': xclk_freq}
        save_dir = "timestamp"
    elif recorder_type == 'recorder':
        RecorderCls = Recorder
        extra_args = {}  # Recorder 不支持 xclk_freq
        save_dir = None
    else:
        raise ValueError("recorder_type 必须是 'fast', 'time', 'timestamp', 'recorder' 之一")

    # 创建测试目录
    test_dir = "/sd/benchmark"
    try:
        uos.rmdir(test_dir)  # 删除旧目录（包括子目录）
    except:
        pass
    try:
        uos.mkdir(test_dir)
    except:
        pass

    results = {}

    for name, framesize in RESOLUTIONS:
        print("\n测试 {}...".format(name))
        try:
            # 创建录制器实例
            if recorder_type == 'fast':
                recorder = RecorderCls(
                    framesize=framesize,
                    quality=10,
                    use_flash=False,
                    keep_camera_open=True,
                    sd_mount_point=test_dir,
                    **extra_args
                )
            else:
                recorder = RecorderCls(
                    framesize=framesize,
                    quality=10,
                    sd_mount_point=test_dir,
                    save_dir=save_dir,
                    **extra_args
                )
            frames, elapsed = recorder.start(duration_sec=duration)
            recorder.close()

            fps = frames / elapsed if elapsed > 0 else 0
            results[name] = (frames, elapsed, fps)
            print("  {} 帧, 耗时 {:.2f} 秒, 帧率 {:.2f} fps".format(frames, elapsed, fps))
        except Exception as e:
            print("  测试失败: {}".format(e))
            results[name] = (0, 0, 0)

        # 回收内存
        gc.collect()

    # 清理测试文件
    print("\n清理测试文件...")
    try:
        # 删除目录及其内容
        uos.rmdir(test_dir)
        print("清理完成")
    except Exception as e:
        print("清理失败: {}".format(e))

    # 按帧率排序（降序）
    sorted_results = sorted(results.items(), key=lambda x: x[1][2], reverse=True)

    # 打印汇总表格
    print("\n" + "="*80)
    print("基准测试结果汇总 (按帧率降序) - 录制器: {}, 时钟: {}".format(
        recorder_type, xclk_freq))
    print("="*80)
    print("{:<20} {:>12} {:>8} {:>10} {:>12}".format("分辨率", "尺寸", "帧数", "耗时(s)", "帧率(fps)"))
    for name, (frames, elapsed, fps) in sorted_results:
        # 获取分辨率尺寸
        framesize = getattr(camera, name)
        w, h = get_resolution(framesize)
        if w is None or h is None:
            size_str = "未知"
        else:
            size_str = "{}×{}".format(w, h)
        print("{:<20} {:>12} {:>8} {:>10.2f} {:>12.2f}".format(name, size_str, frames, elapsed, fps))
    print("="*80)

    return results


if __name__ == "__main__":
    # 示例：使用 FastRecorder 测试 5 秒
    run_benchmark(duration=5, recorder_type='fast')
    # 使用 RecorderTime 测试 5 秒，时钟 20MHz
    # run_benchmark(duration=5, recorder_type='time', xclk_freq=camera.XCLK_20MHz)