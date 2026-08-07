"""
retry_decision.py - 重拍决策模块（重新获取亮度信息）

本模块根据环境亮度信息和重拍指导配置文件（retry_guide.json），
独立判断是否需要重新获取亮度信息（重拍），
与闪光灯决策完全解耦。

核心功能：
    1. load_retry_guide(): 加载重拍指导配置文件（通过 config 模块）
    2. evaluate_retry_decision(): 根据亮度信息评估是否需要重拍
    3. should_retry(): 快速判断是否需要重拍
    4. get_retry_reason(): 获取重拍原因
    5. get_retry_action(): 获取匹配规则的动作（供调用方参考）

设计原则：
    - 与闪光灯决策完全独立
    - 配置文件驱动，便于调整阈值
    - 通过 config 模块统一管理配置
"""
from config import DEBUG as GLOBAL_DEBUG
from config import get_retry_guide_config

# 缓存的配置（避免重复读取）
_cached_guide = None


def _debug_log(msg):
    if GLOBAL_DEBUG:
        print("[RetryDecision] " + msg)


def load_retry_guide():
    """
    加载重拍指导配置文件（通过 config 模块）。

    返回：
        dict: 配置数据，若文件不存在则返回保守默认配置。
    """
    global _cached_guide

    if _cached_guide is not None:
        return _cached_guide

    try:
        _cached_guide = get_retry_guide_config()
        _debug_log("Loaded retry guide via config module")
        return _cached_guide
    except Exception as e:
        _debug_log("Failed to load via config: {}, using minimal default".format(e))
        _cached_guide = _get_minimal_default()
        return _cached_guide


def reload_retry_guide():
    """强制重新加载配置文件。"""
    global _cached_guide
    _cached_guide = None
    return load_retry_guide()


def _get_minimal_default():
    """极简默认配置（当 config 模块也无法提供时使用）。"""
    return {
        "retry_conditions": [
            {
                "id": "invalid_brightness",
                "description": "亮度信息异常（平均<3，动态<2.5，中心<3），建议重新获取亮度信息",
                "condition": "avg < 3 and dynamic < 2.5 and center < 3",
                "action": "retry_analysis"
            }
        ],
        "default_action": {"retry": False}
    }


def _evaluate_condition(condition_str, brightness_info):
    """评估条件字符串（安全）。"""
    avg = brightness_info.get('average_brightness', 0)
    dynamic = brightness_info.get('dynamic_range', 0)
    center = brightness_info.get('center_brightness', 0)
    try:
        expr = condition_str
        expr = expr.replace('avg', str(avg))
        expr = expr.replace('dynamic', str(dynamic))
        expr = expr.replace('center', str(center))
        result = eval(expr)
        return bool(result)
    except Exception as e:
        _debug_log("Condition eval error: {} -> {}".format(condition_str, e))
        return False


def evaluate_retry_decision(brightness_info):
    """
    根据亮度信息评估是否需要重拍（重新获取亮度信息）。

    参数：
        brightness_info (dict): 包含 'average_brightness', 'dynamic_range', 'center_brightness'

    返回：
        dict: {
            'retry': bool,          # 是否需要重拍
            'reason': str,          # 重拍原因描述
            'matched_rule': str,    # 匹配的规则 ID
            'action': str,          # 规则建议的动作（仅供参考）
        }
    """
    guide = load_retry_guide()
    retry_conditions = guide.get('retry_conditions', [])
    default_action = guide.get('default_action', {})

    result = {
        'retry': False,
        'reason': '',
        'matched_rule': '',
        'action': ''
    }

    for cond in retry_conditions:
        cond_str = cond.get('condition', '')
        if _evaluate_condition(cond_str, brightness_info):
            result['retry'] = True
            result['reason'] = cond.get('description', '')
            result['matched_rule'] = cond.get('id', '')
            result['action'] = cond.get('action', '')
            _debug_log("Retry condition matched: {}".format(cond.get('id')))
            break

    if not result['retry']:
        result['retry'] = default_action.get('retry', False)

    return result


def should_retry(brightness_info):
    """快速判断是否需要重拍。"""
    result = evaluate_retry_decision(brightness_info)
    return result.get('retry', False)


def get_retry_reason(brightness_info):
    """获取重拍原因，若不需要重拍则返回空字符串。"""
    result = evaluate_retry_decision(brightness_info)
    return result.get('reason', '')


def get_retry_action(brightness_info):
    """获取匹配规则的 action，供调用方参考。"""
    result = evaluate_retry_decision(brightness_info)
    return result.get('action', '')


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- retry_decision 模块测试 ---")
    test_cases = [
        {"average_brightness": 15.0, "dynamic_range": 20, "center_brightness": 10.0},
        {"average_brightness": 45.0, "dynamic_range": 80, "center_brightness": 35.0},
        {"average_brightness": 75.0, "dynamic_range": 120, "center_brightness": 45.0},
        {"average_brightness": 120.0, "dynamic_range": 50, "center_brightness": 110.0},
        {"average_brightness": 200.0, "dynamic_range": 30, "center_brightness": 190.0},
        {"average_brightness": 60.0, "dynamic_range": 20, "center_brightness": 55.0},
        {"average_brightness": 2.0, "dynamic_range": 2, "center_brightness": 1.0},
    ]

    print("  {:>10} | {:>8} | {:>8} | {:^6} | {:^15}".format(
        "avg", "dynamic", "center", "重拍", "原因"))
    print("  " + "-"*60)

    for info in test_cases:
        result = evaluate_retry_decision(info)
        reason_short = result['reason'][:12] + "..." if len(result['reason']) > 12 else result['reason']
        print("  {:>10} | {:>8} | {:>8} | {:^6} | {}".format(
            info['average_brightness'],
            info['dynamic_range'],
            info['center_brightness'],
            "✅" if result['retry'] else "❌",
            reason_short
        ))