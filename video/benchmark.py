# video/benchmark.py
"""
视频录制帧率基准测试
使用 FastRecorder 测试从 FRAME_96X96 到 FRAME_QXGA 的各个分辨率，
记录每个分辨率在固定时长内的平均帧率。
"""
import time
import gc
import uos
import camera
from .fast_recorder import FastRecorder
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

def run_benchmark(duration=DEFAULT_DURATION):
    """
    执行帧率基准测试。
    参数：
        duration: 每个分辨率的录制秒数
    返回：
        dict: {分辨率名称: (帧数, 耗时秒, 帧率)}
    """
    print("\n开始帧率基准测试...")
    print("每个分辨率录制 {} 秒".format(duration))

    # 创建临时目录存储测试文件
    test_dir = "/sd/benchmark"
    try:
        uos.mkdir(test_dir)
    except:
        pass

    results = {}

    for name, framesize in RESOLUTIONS:
        print("\n测试 {}...".format(name))
        try:
            recorder = FastRecorder(
                framesize=framesize,
                quality=10,
                use_flash=False,
                keep_camera_open=True,
                sd_mount_point=test_dir
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
        files = uos.listdir(test_dir)
        for f in files:
            uos.remove(test_dir + "/" + f)
        uos.rmdir(test_dir)
        print("清理完成")
    except Exception as e:
        print("清理失败: {}".format(e))

    # 按帧率排序（降序）
    sorted_results = sorted(results.items(), key=lambda x: x[1][2], reverse=True)

    # 打印汇总表格
    print("\n" + "="*80)
    print("基准测试结果汇总 (按帧率降序)")
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
    run_benchmark(duration=5)