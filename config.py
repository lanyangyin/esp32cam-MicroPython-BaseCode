"""
config.py - 全局配置模块

本文件提供项目的全局配置变量和函数，目前主要用于调试日志的控制。
所有模块通过 from config import DEBUG 共享同一个调试开关。

设计原则：
    - 集中管理配置，避免分散在各个模块中
    - 提供 set_debug() 函数方便动态切换
    - 各模块在导入时获取 DEBUG 值，运行时通过 set_debug() 动态生效

用法：
    from config import DEBUG, set_debug

    if DEBUG:
        print("Debug mode enabled")

    # 关闭调试日志
    set_debug(False)

    # 开启调试日志
    set_debug(True)
"""
# config.py
# 全局调试开关，所有模块共享
DEBUG = True

def set_debug(enabled):
    """设置调试模式（True 启用日志，False 关闭）。"""
    global DEBUG
    DEBUG = enabled