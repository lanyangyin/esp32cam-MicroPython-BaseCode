# web/__init__.py
"""
Web 控制服务包（基于 EasyWeb 框架）
"""
from .app import start, stop

__all__ = ["start", "stop"]