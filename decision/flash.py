# decision/flash.py
"""闪光灯决策"""
import json
from .engine import evaluate_condition
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="FlashDecision")

DEFAULT_GUIDE_PATH = "/sd/flash_guide.json"
_cached_guide = None

def _get_conservative_default():
    return {
        "flash_conditions": [
            {
                "id": "conservative_very_dark",
                "description": "极暗场景（保守）",
                "condition": "avg < 20",
                "action": "flash_on"
            }
        ],
        "default_action": {"flash": "off"},
        "camera_settings": {
            "scene_profiles": {
                "normal": {"brightness": 0, "contrast": 0, "saturation": 0, "quality": 10}
            }
        }
    }

def load_flash_guide(guide_path=DEFAULT_GUIDE_PATH):
    global _cached_guide
    if _cached_guide is not None:
        return _cached_guide
    try:
        with open(guide_path, 'r') as f:
            _cached_guide = json.load(f)
        _debug_log("Loaded flash guide from {}".format(guide_path))
        return _cached_guide
    except Exception as e:
        _debug_log("Failed to load flash guide: {}, using conservative default".format(e))
        _cached_guide = _get_conservative_default()
        return _cached_guide

def reload_flash_guide(guide_path=DEFAULT_GUIDE_PATH):
    global _cached_guide
    _cached_guide = None
    return load_flash_guide(guide_path)

def evaluate_flash_decision(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    guide = load_flash_guide(guide_path)
    flash_conditions = guide.get('flash_conditions', [])
    default_action = guide.get('default_action', {})
    result = {
        'flash': False,
        'reason': '',
        'matched_rule': '',
        'scene_profile': 'normal'
    }
    for cond in flash_conditions:
        cond_str = cond.get('condition', '')
        if evaluate_condition(cond_str, brightness_info):
            result['flash'] = True
            result['reason'] = cond.get('description', '')
            result['matched_rule'] = cond.get('id', '')
            avg = brightness_info.get('average_brightness', 100)
            if avg < 30:
                result['scene_profile'] = 'very_dark'
            elif avg < 60:
                result['scene_profile'] = 'dark'
            else:
                result['scene_profile'] = 'backlit'
            _debug_log("匹配规则: '{}' -> {}".format(result['matched_rule'], result['reason']))
            _debug_log("场景分类: {}, 平均亮度: {:.1f}".format(result['scene_profile'], avg))
            break
    if not result['flash']:
        result['flash'] = default_action.get('flash') == 'on'
        _debug_log("无匹配规则，使用默认动作: flash={}".format('on' if result['flash'] else 'off'))
    else:
        _debug_log("闪光灯决策结果: {}".format('开启' if result['flash'] else '关闭'))
    return result

def should_use_flash(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    return evaluate_flash_decision(brightness_info, guide_path)['flash']

def get_recommended_settings(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    result = evaluate_flash_decision(brightness_info, guide_path)
    profile_name = result.get('scene_profile', 'normal')
    guide = load_flash_guide(guide_path)
    profiles = guide.get('camera_settings', {}).get('scene_profiles', {})
    return profiles.get(profile_name, profiles.get('normal', {}))