# decision/quick_flash.py
"""
快速闪光灯决策模块
基于平均亮度（avg）快速判断是否需要开启闪光灯。
仅使用简单阈值，不依赖动态范围或中心亮度。
"""
import json
from config import debug_log, LEVEL_INFO, LEVEL_WARNING
from config.camera_model import get_config_path

_cached_quick_guide = None

def _get_quick_guide_path():
    return get_config_path("quick_flash_guide.json")

def _debug_log(msg):
    debug_log(msg, module="QuickFlash")

def _get_conservative_default():
    return {
        "_comment": "快速闪光灯决策配置",
        "threshold": 30,
        "default_action": "off"
    }

def load_quick_flash_guide():
    global _cached_quick_guide
    if _cached_quick_guide is not None:
        return _cached_quick_guide

    path = _get_quick_guide_path()
    try:
        with open(path, 'r') as f:
            _cached_quick_guide = json.load(f)
        _debug_log("Loaded quick flash guide from {}".format(path))
        return _cached_quick_guide
    except Exception as e:
        _debug_log("Failed to load quick flash guide: {}, using conservative default".format(e))
        _cached_quick_guide = _get_conservative_default()
        return _cached_quick_guide

def reload_quick_flash_guide():
    global _cached_quick_guide
    _cached_quick_guide = None
    return load_quick_flash_guide()

def quick_should_use_flash(avg):
    guide = load_quick_flash_guide()
    threshold = guide.get('threshold', 30)
    default_action = guide.get('default_action', 'off')

    if avg < threshold:
        _debug_log("快速闪光灯决策: ON (avg={:.1f} < {})".format(avg, threshold))
        return True
    else:
        result = (default_action == 'on')
        _debug_log("快速闪光灯决策: {} (avg={:.1f} >= {})".format(
            'ON' if result else 'OFF', avg, threshold))
        return result

def set_quick_flash_threshold(threshold):
    config = load_quick_flash_guide()
    config['threshold'] = threshold
    path = _get_quick_guide_path()
    try:
        with open(path, 'w') as f:
            json.dump(config, f)
        _debug_log("Quick flash threshold updated to {}".format(threshold))
        global _cached_quick_guide
        _cached_quick_guide = config
    except Exception as e:
        _debug_log("Failed to save quick flash guide: {}".format(e))
        raise