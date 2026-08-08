# video/__init__.py
from .recorder import VideoRecorder
from .fast_recorder import FastRecorder
from .fast_recorder_no_flash import FastRecorderNoFlash
from .fast_recorder_by_frames_thread import FastRecorderByFrames
from .fast_recorder_by_frames_single import FastRecorderByFramesSingle
from .benchmark import run_benchmark

__all__ = [
    "VideoRecorder",
    "FastRecorder",
    "FastRecorderNoFlash",
    "FastRecorderByFrames",
    "FastRecorderByFramesSingle",
    "run_benchmark"
]