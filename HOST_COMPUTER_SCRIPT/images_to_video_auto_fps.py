#!/usr/bin/env python3
"""
根据文件名中的毫秒时间戳自动计算帧率，合成 MP4 视频。
支持两种输入方式：
  1. 图片目录：python images_to_video_auto_fps.py --input /path/to/images
  2. 归档文件 (.arc)：python images_to_video_auto_fps.py --input /path/to/archive.arc

如果不指定 --fps，则自动从时间戳计算。
如果不指定 --output，默认在输入目录（或归档所在目录）生成 output.mp4。
"""

import os
import sys
import argparse
import re
import cv2
import numpy as np
import tempfile
import shutil
from statistics import median

# ---------- 归档解压函数 (与 ESP32 端兼容) ----------
ARCHIVE_MAGIC = "---FILE_START---"
ARCHIVE_END = "---FILE_END---"

def _ensure_dir(path):
    """确保目录存在，自动创建父目录（兼容 Windows/Linux）"""
    if not path:
        return
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def extract_archive(archive_path, target_dir):
    """
    解压 .arc 归档文件到目标目录。
    返回成功解压的文件路径列表。
    """
    extracted = []
    try:
        with open(archive_path, 'rb') as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.decode().strip()
                if line == ARCHIVE_MAGIC:
                    # 读文件名
                    name_line = f.readline()
                    if not name_line:
                        break
                    rel_path = name_line.decode().strip()
                    # 读文件大小
                    size_line = f.readline()
                    if not size_line:
                        break
                    try:
                        size = int(size_line.decode().strip())
                    except ValueError:
                        break
                    # 读文件数据
                    data = f.read(size)
                    if len(data) != size:
                        break
                    # 读结束标记
                    end_line = f.readline()
                    if end_line:
                        end_line = end_line.decode().strip()
                        if end_line == ARCHIVE_END:
                            target_full = os.path.join(target_dir, rel_path)
                            parent = os.path.dirname(target_full)
                            _ensure_dir(parent)
                            with open(target_full, 'wb') as out:
                                out.write(data)
                            extracted.append(target_full)
                        else:
                            print(f"警告: 结束标记不匹配，跳过 {rel_path}")
                    else:
                        break
                else:
                    continue
    except Exception as e:
        print(f"解压失败: {e}")
        return []
    return extracted

# ---------- 原有视频合成逻辑 ----------
def get_timestamp_from_filename(filename):
    base = os.path.splitext(filename)[0]
    if base.isdigit():
        return int(base)
    nums = re.findall(r'\d+', base)
    if nums:
        return int(max(nums, key=len))
    raise ValueError(f"无法从文件名 '{filename}' 提取时间戳")

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', s)]

def synthesize_video_from_images(image_dir, output_path, fps_override=None):
    """从图片目录合成视频（原核心逻辑）"""
    files = [f for f in os.listdir(image_dir)
             if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
    if not files:
        print(f"错误: 目录 '{image_dir}' 中没有找到 JPG 文件")
        return False

    files.sort(key=natural_sort_key)
    print(f"找到 {len(files)} 张图片")

    timestamps = []
    for fname in files:
        try:
            ts = get_timestamp_from_filename(fname)
            timestamps.append(ts)
        except ValueError as e:
            print(f"警告: {e}，跳过该文件")

    if len(timestamps) < 2:
        print("错误: 有效图片少于2张，无法计算帧率")
        return False

    diffs = []
    for i in range(1, len(timestamps)):
        diff = timestamps[i] - timestamps[i-1]
        if diff > 0:
            diffs.append(diff)

    if not diffs:
        print("错误: 无法计算帧间隔，所有时间差为0或负")
        return False

    median_diff = median(diffs)
    avg_diff = sum(diffs) / len(diffs)

    if fps_override is not None:
        fps = fps_override
        print(f"使用手动指定的帧率: {fps:.2f} fps")
    else:
        fps = 1000.0 / median_diff
        print(f"根据时间戳自动计算:")
        print(f"  时间戳数量: {len(timestamps)}")
        print(f"  有效间隔数: {len(diffs)}")
        print(f"  平均间隔: {avg_diff:.2f} ms")
        print(f"  中位间隔: {median_diff:.2f} ms")
        print(f"  自动帧率: {fps:.2f} fps")

    # 读取第一张图片获取尺寸
    first_img_path = os.path.join(image_dir, files[0])
    frame = cv2.imread(first_img_path)
    if frame is None:
        print(f"错误: 无法读取第一张图片 '{first_img_path}'")
        return False
    height, width, _ = frame.shape
    print(f"图片尺寸: {width}x{height}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"错误: 无法创建视频文件 '{output_path}'")
        return False

    print(f"开始合成视频，目标帧率: {fps:.2f} fps")
    count = 0
    for fname in files:
        img_path = os.path.join(image_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"警告: 跳过无法读取的图片 '{fname}'")
            continue
        if img.shape[1] != width or img.shape[0] != height:
            img = cv2.resize(img, (width, height))
        out.write(img)
        count += 1
        if count % 100 == 0:
            print(f"已处理 {count} 帧")

    out.release()
    print(f"完成！共写入 {count} 帧，视频保存至: {output_path}")
    return True

# ---------- 主函数 ----------
def main():
    parser = argparse.ArgumentParser(
        description="从图片目录或 .arc 归档文件合成视频（自动帧率）"
    )
    parser.add_argument("--input", required=True,
                        help="输入：图片目录 或 .arc 归档文件路径")
    parser.add_argument("--output", default=None,
                        help="输出视频文件路径 (默认: 输入目录下 output.mp4 或归档同目录 output.mp4)")
    parser.add_argument("--fps", type=float, default=None,
                        help="手动指定帧率（覆盖自动计算）")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"错误: 路径 '{input_path}' 不存在")
        sys.exit(1)

    # 判断输入是目录还是 .arc 文件
    is_arc = os.path.isfile(input_path) and input_path.lower().endswith('.arc')
    is_dir = os.path.isdir(input_path)

    if not is_arc and not is_dir:
        print(f"错误: 输入必须是目录或 .arc 归档文件，当前为: {input_path}")
        sys.exit(1)

    # 确定输出路径
    if args.output is None:
        if is_dir:
            output_path = os.path.join(input_path, "output.mp4")
        else:  # is_arc
            dirname = os.path.dirname(input_path)
            basename = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(dirname, f"{basename}.mp4")
    else:
        # 如果 output 是目录，则自动拼接文件名
        if os.path.isdir(args.output):
            if is_arc:
                basename = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(args.output, f"{basename}.mp4")
            else:
                output_path = os.path.join(args.output, "output.mp4")
        else:
            output_path = args.output

    # 如果输入是目录，直接合成
    if is_dir:
        success = synthesize_video_from_images(input_path, output_path, args.fps)
        sys.exit(0 if success else 1)

    # 输入是 .arc 归档文件
    print(f"检测到归档文件: {input_path}")
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="arc_extract_")
    print(f"解压到临时目录: {temp_dir}")

    extracted = extract_archive(input_path, temp_dir)
    if not extracted:
        print("错误: 解压失败或无文件")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
    print(f"成功解压 {len(extracted)} 个文件")

    # 确保临时目录中有图片
    image_files = []
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg'):
                image_files.append(os.path.join(root, f))
    if not image_files:
        print("错误: 归档中未找到 JPG 图片")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)

    # 合成视频
    success = synthesize_video_from_images(temp_dir, output_path, args.fps)

    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("临时目录已清理")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()