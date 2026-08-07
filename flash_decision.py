"""
flash_decision.py - 智能闪光灯决策模块

本模块根据环境亮度信息和闪光灯指导配置文件（flash_guide.json），
自动判断是否需要开启闪光灯。

核心功能：
    1. load_flash_guide(): 加载闪光灯指导配置文件
    2. evaluate_flash_decision(): 根据亮度信息评估是否开闪光灯
    3. should_use_flash(): 快速判断是否开启闪光灯
    4. get_recommended_settings(): 获取推荐摄像头参数

设计原则：
    - 决策逻辑与硬件控制分离
    - 配置文件驱动，便于调整阈值
    - 与重拍决策完全解耦
"""
import json

from config import DEBUG as GLOBAL_DEBUG

# 默认配置文件路径
DEFAULT_GUIDE_PATH = "/sd/flash_guide.json"

# 缓存的配置（避免重复读取）
_cached_guide = None


def _debug_log(msg):
    if GLOBAL_DEBUG:
        print("[FlashDecision] " + msg)


def load_flash_guide(guide_path=DEFAULT_GUIDE_PATH):
    """
    加载闪光灯指导配置文件。

    参数：
        guide_path (str): 配置文件路径，默认 /sd/flash_guide.json

    返回：
        dict: 配置数据，若文件不存在则返回保守默认配置。
    """
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
    """强制重新加载配置文件。"""
    global _cached_guide
    _cached_guide = None
    return load_flash_guide(guide_path)


def _get_conservative_default():
    """返回极简保守默认配置（仅极暗场景开闪光灯）。"""
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


def evaluate_flash_decision(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    """
    根据亮度信息评估是否开启闪光灯。

    参数：
        brightness_info (dict): 包含 'average_brightness', 'dynamic_range', 'center_brightness'
        guide_path (str): 配置文件路径。

    返回：
        dict: {
            'flash': bool,          # 是否开启闪光灯
            'reason': str,          # 决策原因描述
            'matched_rule': str,    # 匹配的规则 ID
            'scene_profile': str,   # 推荐场景配置名称
        }
    """
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
        if _evaluate_condition(cond_str, brightness_info):
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
            break

    if not result['flash']:
        result['flash'] = default_action.get('flash') == 'on'

    _debug_log("Flash decision: {}".format(result['flash']))
    return result


def should_use_flash(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    """快速判断是否开启闪光灯。"""
    result = evaluate_flash_decision(brightness_info, guide_path)
    return result.get('flash', False)


def get_recommended_settings(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    """获取推荐摄像头参数。"""
    result = evaluate_flash_decision(brightness_info, guide_path)
    profile_name = result.get('scene_profile', 'normal')
    guide = load_flash_guide(guide_path)
    profiles = guide.get('camera_settings', {}).get('scene_profiles', {})
    settings = profiles.get(profile_name, profiles.get('normal', {}))
    _debug_log("Recommended settings for {}: {}".format(profile_name, settings))
    return settings


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  flash_decision 模块测试")
    print("="*50)

    test_cases = [
        {"average_brightness": 15.0, "dynamic_range": 20, "center_brightness": 10.0},
        {"average_brightness": 45.0, "dynamic_range": 80, "center_brightness": 35.0},
        {"average_brightness": 75.0, "dynamic_range": 120, "center_brightness": 45.0},
        {"average_brightness": 120.0, "dynamic_range": 50, "center_brightness": 110.0},
        {"average_brightness": 200.0, "dynamic_range": 30, "center_brightness": 190.0},
        {"average_brightness": 60.0, "dynamic_range": 20, "center_brightness": 55.0},
        {"average_brightness": 2.0, "dynamic_range": 2, "center_brightness": 1.0},
    ]

    print("  {:>10} | {:>8} | {:>8} | {:^6} | {:^12}".format(
        "avg", "dynamic", "center", "闪光", "场景配置"))
    print("  " + "-"*60)

    for info in test_cases:
        result = evaluate_flash_decision(info)
        print("  {:>10} | {:>8} | {:>8} | {:^6} | {:^12}".format(
            info['average_brightness'],
            info['dynamic_range'],
            info['center_brightness'],
            "✅" if result['flash'] else "❌",
            result['scene_profile']
        ))

    print("\n" + "="*50)