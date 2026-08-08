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
from .recorder_frames import RecorderFrames
from camera_driver.resolutions import get_resolution

# 要测试的分辨率（名称和常量）
RESOLUTIONS = [
    # ("FRAME_96X96", camera.FRAME_96X96),
    # ("FRAME_QQVGA", camera.FRAME_QQVGA),
    # ("FRAME_QCIF", camera.FRAME_QCIF),
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

# 每个分辨率录制时长（秒）或帧数
DEFAULT_DURATION = 5          # 适用于时长类录制器
DEFAULT_FRAMES = 200          # 适用于帧数类录制器（RecorderFrames）

def _remove_dir(path):
    """递归删除目录及其所有内容（稳健版）"""
    try:
        # 列出所有文件/目录
        items = uos.listdir(path)
        for item in items:
            full = path + "/" + item
            try:
                # 尝试删除文件，如果是目录则递归
                uos.remove(full)
            except OSError:
                # 可能是目录，递归删除
                _remove_dir(full)
        uos.rmdir(path)
    except OSError as e:
        # 目录可能不存在，忽略
        pass

def run_benchmark(duration=DEFAULT_DURATION, recorder_type='fast',
                  xclk_freq=camera.XCLK_10MHz, target_frames=DEFAULT_FRAMES):
    """
    执行帧率基准测试。

    参数：
        duration (int): 每个分辨率的录制秒数（仅对时长类录制器有效）
        recorder_type (str): 录制器类型，可选 'fast', 'time', 'timestamp', 'recorder', 'frames'
            - 'fast'      : 使用 FastRecorder（极速，可保持摄像头常开，无日志）
            - 'time'      : 使用 RecorderTime（按时间录制，14秒GC，序号文件名）
            - 'timestamp' : 使用 RecorderTimestamp（按时间录制，14秒GC，时间戳文件名）
            - 'recorder'  : 使用 Recorder（通用录制器，有日志和闪光灯支持）
            - 'frames'    : 使用 RecorderFrames（按帧数录制，50帧GC，固定帧数）
        xclk_freq (int): 摄像头时钟频率，仅在 'time' 和 'timestamp' 模式下有效
        target_frames (int): 当 recorder_type='frames' 时，每个分辨率录制的总帧数

    返回：
        dict: {分辨率名称: (帧数, 耗时秒, 帧率)}
    """
    print("\n开始帧率基准测试...")
    print("录制器类型: {}, 时钟频率: {}".format(recorder_type, xclk_freq))

    # 选择录制器类
    recorder_map = {
        'fast': (FastRecorder, {'keep_camera_open': True}),
        'time': (RecorderTime, {}),
        'timestamp': (RecorderTimestamp, {}),
        'recorder': (Recorder, {}),
        'frames': (RecorderFrames, {}),
    }
    if recorder_type not in recorder_map:
        raise ValueError("recorder_type 必须是 'fast', 'time', 'timestamp', 'recorder', 'frames' 之一")

    RecorderCls, extra_fixed = recorder_map[recorder_type]
    use_frames = (recorder_type == 'frames')
    save_dir = None if recorder_type == 'fast' or recorder_type == 'recorder' else recorder_type

    # 创建测试目录
    test_dir = "/sd/benchmark"
    _remove_dir(test_dir)          # 先清空旧目录
    try:
        uos.mkdir(test_dir)
    except:
        pass

    results = {}

    for name, framesize in RESOLUTIONS:
        print("\n测试 {}...".format(name))
        try:
            # 构建参数
            common_args = {
                'framesize': framesize,
                'quality': 10,
                'sd_mount_point': test_dir,
                'xclk_freq': xclk_freq,   # 统一传递
            }
            if save_dir is not None:
                common_args['save_dir'] = save_dir
            if recorder_type == 'fast':
                common_args.update(extra_fixed)  # keep_camera_open
            else:
                common_args.update(extra_fixed)

            recorder = RecorderCls(**common_args)

            if use_frames:
                frames, elapsed = recorder.start(total_frames=target_frames)
            else:
                frames, elapsed = recorder.start(duration_sec=duration)
            recorder.close()

            fps = frames / elapsed if elapsed > 0 else 0
            results[name] = (frames, elapsed, fps)
            print("  {} 帧, 耗时 {:.2f} 秒, 帧率 {:.2f} fps".format(frames, elapsed, fps))
        except Exception as e:
            print("  测试失败: {}".format(e))
            results[name] = (0, 0, 0)

        gc.collect()

    # 清理测试目录
    print("\n清理测试文件...")
    _remove_dir(test_dir)
    print("清理完成")

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
    # 使用 RecorderFrames 录制 200 帧
    # run_benchmark(recorder_type='frames', target_frames=200, xclk_freq=camera.XCLK_20MHz)