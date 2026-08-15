# decision/flash.py
"""闪光灯决策"""
import json
from config import debug_log
from config.camera_model import get_config_path
from .engine import evaluate_condition

_cached_guide = None

def _get_flash_guide_path():
    return get_config_path("flash_guide.json")

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

def load_flash_guide():
    global _cached_guide
    if _cached_guide is not None:
        return _cached_guide
    path = _get_flash_guide_path()
    try:
        with open(path, 'r') as f:
            _cached_guide = json.load(f)
        debug_log("Loaded flash guide from {}".format(path), module="FlashDecision")
        return _cached_guide
    except Exception as e:
        debug_log("Failed to load flash guide: {}, using conservative default".format(e), module="FlashDecision")
        _cached_guide = _get_conservative_default()
        return _cached_guide

def reload_flash_guide():
    global _cached_guide
    _cached_guide = None
    return load_flash_guide()

def evaluate_flash_decision(brightness_info):
    guide = load_flash_guide()
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
            debug_log("匹配规则: '{}' -> {}".format(result['matched_rule'], result['reason']), module="FlashDecision")
            debug_log("场景分类: {}, 平均亮度: {:.1f}".format(result['scene_profile'], avg), module="FlashDecision")
            break
    if not result['flash']:
        result['flash'] = default_action.get('flash') == 'on'
        debug_log("无匹配规则，使用默认动作: flash={}".format('on' if result['flash'] else 'off'), module="FlashDecision")
    else:
        debug_log("闪光灯决策结果: {}".format('开启' if result['flash'] else '关闭'), module="FlashDecision")
    return result

def should_use_flash(brightness_info):
    return evaluate_flash_decision(brightness_info)['flash']

def get_recommended_settings(brightness_info):
    result = evaluate_flash_decision(brightness_info)
    profile_name = result.get('scene_profile', 'normal')
    guide = load_flash_guide()
    profiles = guide.get('camera_settings', {}).get('scene_profiles', {})
    return profiles.get(profile_name, profiles.get('normal', {}))