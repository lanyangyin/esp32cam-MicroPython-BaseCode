# config.py
# 全局调试开关，所有模块共享
DEBUG = True

def set_debug(enabled):
    """设置调试模式（True 启用日志，False 关闭）。"""
    global DEBUG
    DEBUG = enabled