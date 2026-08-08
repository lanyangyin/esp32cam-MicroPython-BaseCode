# decision/engine.py
"""共享评估引擎"""
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="DecisionEngine")


def evaluate_condition(condition_str, brightness_info):
    """评估条件字符串，支持 avg, dynamic, center, rms 变量"""
    avg = brightness_info.get('average_brightness', 0)
    dynamic = brightness_info.get('dynamic_range', 0)
    center = brightness_info.get('center_brightness', 0)
    rms = brightness_info.get('rms_contrast', 0)   # 新增 rms
    try:
        expr = condition_str
        expr = expr.replace('avg', str(avg))
        expr = expr.replace('dynamic', str(dynamic))
        expr = expr.replace('center', str(center))
        expr = expr.replace('rms', str(rms))
        result = eval(expr)
        return bool(result)
    except Exception as e:
        _debug_log("Condition eval error: {} -> {}".format(condition_str, e))
        return False