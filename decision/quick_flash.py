# decision/quick_flash.py
"""
快速闪光灯决策模块
基于平均亮度（avg）快速判断是否需要开启闪光灯。
仅使用简单阈值，不依赖动态范围或中心亮度。
"""
import json
from config import debug_log, LEVEL_INFO, LEVEL_WARNING

DEFAULT_QUICK_GUIDE_PATH = "/sd/quick_flash_guide.json"
_cached_quick_guide = None


def _debug_log(msg):
    debug_log(msg, module="QuickFlash")


def _get_conservative_default():
    """返回保守默认配置（阈值 30）"""
    return {
        "_comment": "快速闪光灯决策配置",
        "threshold": 30,  # avg < 30 时开闪光灯
        "default_action": "off"
    }


def load_quick_flash_guide(guide_path=DEFAULT_QUICK_GUIDE_PATH):
    """
    加载快速闪光灯决策配置文件。
    若文件不存在，返回保守默认配置。
    """
    global _cached_quick_guide
    if _cached_quick_guide is not None:
        return _cached_quick_guide

    try:
        with open(guide_path, 'r') as f:
            _cached_quick_guide = json.load(f)
        _debug_log("Loaded quick flash guide from {}".format(guide_path))
        return _cached_quick_guide
    except Exception as e:
        _debug_log("Failed to load quick flash guide: {}, using conservative default".format(e))
        _cached_quick_guide = _get_conservative_default()
        return _cached_quick_guide


def reload_quick_flash_guide(guide_path=DEFAULT_QUICK_GUIDE_PATH):
    """强制重新加载配置文件"""
    global _cached_quick_guide
    _cached_quick_guide = None
    return load_quick_flash_guide(guide_path)


def quick_should_use_flash(avg, guide_path=DEFAULT_QUICK_GUIDE_PATH):
    """
    基于平均亮度快速判断是否开启闪光灯。
    参数：
        avg (float): 平均亮度（0~255），来自 quick_brightness_estimate
        guide_path (str): 配置文件路径
    返回：
        bool: True 表示需要开闪光灯
    """
    guide = load_quick_flash_guide(guide_path)
    threshold = guide.get('threshold', 30)
    default_action = guide.get('default_action', 'off')

    # 若 avg 低于阈值，开闪光灯
    if avg < threshold:
        _debug_log("快速闪光灯决策: ON (avg={:.1f} < {})".format(avg, threshold))
        return True
    else:
        # 否则按默认动作
        result = (default_action == 'on')
        _debug_log("快速闪光灯决策: {} (avg={:.1f} >= {})".format(
            'ON' if result else 'OFF', avg, threshold))
        return result


def set_quick_flash_threshold(threshold, guide_path=DEFAULT_QUICK_GUIDE_PATH):
    """
    动态设置快速闪光灯阈值，并保存到配置文件。
    参数：
        threshold (int/float): 新的阈值
        guide_path (str): 配置文件路径
    """
    config = load_quick_flash_guide(guide_path)
    config['threshold'] = threshold
    try:
        with open(guide_path, 'w') as f:
            json.dump(config, f)
        _debug_log("Quick flash threshold updated to {}".format(threshold))
        # 清除缓存，以便下次重新加载
        global _cached_quick_guide
        _cached_quick_guide = config
    except Exception as e:
        _debug_log("Failed to save quick flash guide: {}".format(e))
        raise


if __name__ == "__main__":
    # 测试快速闪光灯决策
    print("快速闪光灯决策测试")
    test_avgs = [10, 25, 30, 40, 50]
    for avg in test_avgs:
        result = quick_should_use_flash(avg)
        print("avg={:.1f} -> flash={}".format(avg, result))