# decision/retry.py
"""重拍决策（重新获取亮度信息）"""
from config import get_retry_guide_config
from .engine import evaluate_condition
from config import DEBUG

_cached_guide = None

def _debug_log(msg):
    if DEBUG:
        print("[RetryDecision] " + msg)

def load_retry_guide():
    global _cached_guide
    if _cached_guide is not None:
        return _cached_guide
    try:
        _cached_guide = get_retry_guide_config()
        _debug_log("Loaded retry guide via config module")
        return _cached_guide
    except Exception as e:
        _debug_log("Failed to load via config: {}, using minimal default".format(e))
        _cached_guide = {
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
        return _cached_guide

def reload_retry_guide():
    global _cached_guide
    _cached_guide = None
    return load_retry_guide()

def evaluate_retry_decision(brightness_info):
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
        if evaluate_condition(cond_str, brightness_info):
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
    return evaluate_retry_decision(brightness_info)['retry']

def get_retry_reason(brightness_info):
    return evaluate_retry_decision(brightness_info)['reason']

def get_retry_action(brightness_info):
    return evaluate_retry_decision(brightness_info)['action']