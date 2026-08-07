# config/debug.py
"""
全局调试开关和日志工具
"""
import time

# 调试开关（终端输出）
DEBUG = True

# 日志文件开关
LOG_TO_FILE = True
LOG_FILE_PATH = "/sd/debug.log"


def set_debug(enabled):
    """设置是否输出调试信息到终端"""
    global DEBUG
    DEBUG = enabled


def set_log_to_file(enabled, file_path=None):
    """
    设置是否将日志写入文件
    参数：
        enabled: bool，True 写入文件
        file_path: str，日志文件路径，默认 /sd/debug.log
    """
    global LOG_TO_FILE, LOG_FILE_PATH
    LOG_TO_FILE = enabled
    if file_path is not None:
        LOG_FILE_PATH = file_path


def debug_log(msg, module=""):
    """
    统一的日志输出函数。
    如果 DEBUG 为 True，则输出到终端（print）。
    如果 LOG_TO_FILE 为 True，则追加到日志文件。
    参数：
        msg: 日志消息字符串
        module: 模块名（可选），用于标识来源
    """
    if not DEBUG and not LOG_TO_FILE:
        return

    # 构造前缀
    if module:
        log_line = "[{}] {}".format(module, msg)
    else:
        log_line = msg

    # 添加时间戳
    t = time.localtime()
    time_str = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    full_line = "[{}] {}".format(time_str, log_line)

    if DEBUG:
        print(full_line)

    if LOG_TO_FILE:
        try:
            with open(LOG_FILE_PATH, "a") as f:
                f.write(full_line + "\n")
        except:
            pass  # 忽略文件写入错误