#!/usr/bin/env python3
"""
根据文件名中的毫秒时间戳自动计算帧率，合成 MP4 视频。

用法：
    python images_to_video_auto_fps.py --input_dir /path/to/images [--output out.mp4] [--fps 覆盖值]

如果不指定 --fps，则自动从时间戳计算。
如果不指定 --output，默认在输入目录生成 output.mp4。
"""

import os
import sys
import argparse
import re
import cv2
import numpy as np
from statistics import median

def get_timestamp_from_filename(filename):
    """从文件名中提取数字（假设是整个文件名去掉扩展名后的数字）"""
    base = os.path.splitext(filename)[0]
    # 如果文件名是纯数字，直接转换
    if base.isdigit():
        return int(base)
    # 否则尝试匹配数字
    nums = re.findall(r'\d+', base)
    if nums:
        # 取最长的数字串（通常是时间戳）
        return int(max(nums, key=len))
    raise ValueError(f"无法从文件名 '{filename}' 提取时间戳")

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', s)]

def main():
    parser = argparse.ArgumentParser(description="自动根据时间戳帧率合成视频")
    parser.add_argument("--input_dir", required=True,
                        help="包含 JPG 图片的目录")
    parser.add_argument("--output", default=None,
                        help="输出视频文件路径 (默认: 输入目录/output.mp4)")
    parser.add_argument("--fps", type=float, default=None,
                        help="手动指定帧率（覆盖自动计算）")
    parser.add_argument("--ext", default=".jpg",
                        help="图片扩展名 (默认: .jpg)")
    args = parser.parse_args()

    input_dir = args.input_dir
    if not os.path.isdir(input_dir):
        print(f"错误: 目录 '{input_dir}' 不存在")
        sys.exit(1)

    # 收集所有图片文件
    files = [f for f in os.listdir(input_dir)
             if f.lower().endswith(args.ext.lower())]
    if not files:
        print(f"错误: 目录 '{input_dir}' 中没有找到 {args.ext} 文件")
        sys.exit(1)

    # 按文件名排序（数字顺序）
    files.sort(key=natural_sort_key)
    print(f"找到 {len(files)} 张图片")

    # 提取时间戳列表
    timestamps = []
    for fname in files:
        try:
            ts = get_timestamp_from_filename(fname)
            timestamps.append(ts)
        except ValueError as e:
            print(f"警告: {e}，跳过该文件")
            continue

    if len(timestamps) < 2:
        print("错误: 有效图片少于2张，无法计算帧率")
        sys.exit(1)

    # 计算帧间隔（毫秒）
    diffs = []
    for i in range(1, len(timestamps)):
        diff = timestamps[i] - timestamps[i-1]
        if diff > 0:  # 忽略负值或零（异常）
            diffs.append(diff)

    if not diffs:
        print("错误: 无法计算帧间隔，所有时间差为0或负")
        sys.exit(1)

    # 使用中位数抵抗抖动
    median_diff = median(diffs)
    avg_diff = sum(diffs) / len(diffs)

    # 决定实际使用的帧率
    if args.fps is not None:
        fps = args.fps
        print(f"使用手动指定的帧率: {fps:.2f} fps")
    else:
        # 用中位数计算帧率
        fps = 1000.0 / median_diff
        print(f"根据时间戳自动计算:")
        print(f"  时间戳数量: {len(timestamps)}")
        print(f"  有效间隔数: {len(diffs)}")
        print(f"  平均间隔: {avg_diff:.2f} ms")
        print(f"  中位间隔: {median_diff:.2f} ms")
        print(f"  自动帧率: {fps:.2f} fps")

    # 确定输出路径
    if args.output is None:
        output_path = os.path.join(input_dir, "output.mp4")
    else:
        output_path = args.output

    # 读取第一张图片获取尺寸
    first_img_path = os.path.join(input_dir, files[0])
    frame = cv2.imread(first_img_path)
    if frame is None:
        print(f"错误: 无法读取第一张图片 '{first_img_path}'")
        sys.exit(1)
    height, width, _ = frame.shape
    print(f"图片尺寸: {width}x{height}")

    # 初始化视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"错误: 无法创建视频文件 '{output_path}'")
        sys.exit(1)

    print(f"开始合成视频，目标帧率: {fps:.2f} fps")
    count = 0
    for fname in files:
        img_path = os.path.join(input_dir, fname)
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

if __name__ == "__main__":
    main()