# web/__init__.py
"""
Web 控制服务包（基于 EasyWeb 框架）
提供 HTTP 服务器，允许通过浏览器远程控制摄像头拍照和录像。
"""
from .app import app

def start(host="0.0.0.0", port=80):
    """启动 Web 服务器"""
    app.run(host, port)

def stop():
    """停止 Web 服务器"""
    if app.server:
        app.stop()

__all__ = ["start", "stop"]