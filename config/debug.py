# config/debug.py
"""
全局调试开关和日志工具（支持分级）
"""
import time

# ---------- 日志级别常量 ----------
LEVEL_DEBUG = 10
LEVEL_INFO = 20
LEVEL_WARNING = 30
LEVEL_ERROR = 40
LEVEL_CRITICAL = 50

LEVEL_NAMES = {
    LEVEL_DEBUG: "DEBUG",
    LEVEL_INFO: "INFO",
    LEVEL_WARNING: "WARNING",
    LEVEL_ERROR: "ERROR",
    LEVEL_CRITICAL: "CRITICAL",
}

# 当前全局最低日志级别（默认 INFO）
_LOG_LEVEL = LEVEL_INFO

# 调试开关（终端输出）
DEBUG = True

# 日志文件开关
LOG_TO_FILE = False
LOG_FILE_PATH = "/sd/debug.log"


def set_debug(enabled):
    """设置是否输出调试信息到终端"""
    global DEBUG
    DEBUG = enabled


def set_log_level(level):
    """
    设置全局日志最低输出级别。
    参数：level 为 LEVEL_DEBUG / LEVEL_INFO / LEVEL_WARNING / LEVEL_ERROR / LEVEL_CRITICAL
    """
    global _LOG_LEVEL
    _LOG_LEVEL = level


def get_log_level():
    """获取当前日志级别"""
    return _LOG_LEVEL


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


def debug_log(msg, level=LEVEL_INFO, module=""):
    """
    统一的日志输出函数。
    如果当前级别低于全局级别，则不输出。
    如果 DEBUG 为 True，则输出到终端。
    如果 LOG_TO_FILE 为 True，则追加到日志文件。

    参数：
        msg: 日志消息字符串
        level: 日志级别（LEVEL_* 常量），默认为 INFO
        module: 模块名（可选），用于标识来源
    """
    # 级别过滤
    if level < _LOG_LEVEL:
        return

    if not DEBUG and not LOG_TO_FILE:
        return

    # 获取级别名称
    level_name = LEVEL_NAMES.get(level, "UNKNOWN")

    # 构造前缀
    if module:
        log_line = "[{}] [{}] {}".format(module, level_name, msg)
    else:
        log_line = "[{}] {}".format(level_name, msg)

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