# video/__init__.py
from .recorder import VideoRecorder
from .fast_recorder import FastRecorder
from .benchmark import run_benchmark

__all__ = ["VideoRecorder", "FastRecorder", "run_benchmark"]