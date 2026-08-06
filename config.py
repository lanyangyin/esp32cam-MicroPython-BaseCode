"""
config.py - 全局配置模块

本文件提供项目的全局配置变量和函数，目前主要用于调试日志的控制。
所有模块通过 from config import DEBUG 共享同一个调试开关。

扩展功能：
    - 闪光灯指导配置文件（flash_guide.json）的增删改查操作
    - 重拍指导配置文件（retry_guide.json）的增删改查操作
    - 提供极简保守默认配置（文件不存在时使用）

设计原则：
    - 集中管理配置，避免分散在各个模块中
    - 提供 set_debug() 函数方便动态切换
    - 默认配置极简，减少内存占用

用法：
    from config import DEBUG, set_debug

    if DEBUG:
        print("Debug mode enabled")

    # 关闭调试日志
    set_debug(False)

    # 开启调试日志
    set_debug(True)

    # 闪光灯配置文件操作
    from config import get_flash_guide_config, add_flash_rule
    config = get_flash_guide_config()
    add_flash_rule({"id": "my_rule", ...})

    # 重拍配置文件操作
    from config import get_retry_guide_config, add_retry_rule
    retry_config = get_retry_guide_config()
    add_retry_rule({"id": "my_retry_rule", ...})
"""
import json

# 全局调试开关，所有模块共享
DEBUG = True

# 配置文件路径
FLASH_GUIDE_PATH = "/sd/flash_guide.json"
RETRY_GUIDE_PATH = "/sd/retry_guide.json"

# 缓存配置
_cached_flash_guide = None
_cached_retry_guide = None


def set_debug(enabled):
    """设置调试模式（True 启用日志，False 关闭）。"""
    global DEBUG
    DEBUG = enabled


# ==================== 闪光灯配置文件操作 ====================

def get_flash_guide_config(force_reload=False):
    """
    获取闪光灯指导配置。

    若 SD 卡配置文件不存在，返回极简保守配置。
    若文件存在，加载并缓存。

    参数：
        force_reload (bool): 是否强制重新从文件加载。

    返回：
        dict: 配置数据。
    """
    global _cached_flash_guide

    if _cached_flash_guide is not None and not force_reload:
        return _cached_flash_guide

    try:
        with open(FLASH_GUIDE_PATH, 'r') as f:
            _cached_flash_guide = json.load(f)
        if DEBUG:
            print("[Config] Loaded flash guide from {}".format(FLASH_GUIDE_PATH))
        return _cached_flash_guide
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to load flash guide: {}, using conservative default".format(e))
        _cached_flash_guide = _get_flash_conservative_default()
        return _cached_flash_guide


def update_flash_guide_config(new_config, save_to_file=True):
    """更新闪光灯指导配置（与现有配置合并）。"""
    global _cached_flash_guide
    current = get_flash_guide_config()
    merged = _deep_merge(current, new_config)
    _cached_flash_guide = merged
    if save_to_file:
        try:
            with open(FLASH_GUIDE_PATH, 'w') as f:
                json.dump(merged, f)
            if DEBUG:
                print("[Config] Saved flash guide to {}".format(FLASH_GUIDE_PATH))
        except Exception as e:
            if DEBUG:
                print("[Config] Failed to save flash guide: {}".format(e))
    return merged


def add_flash_rule(rule_data):
    """
    添加一条闪光灯决策规则到 flash_conditions 列表。

    参数：
        rule_data (dict): 规则数据，必须包含 'id', 'description', 'condition', 'action'。

    返回：
        dict: 更新后的完整配置。
    """
    current = get_flash_guide_config()
    if 'flash_conditions' not in current:
        current['flash_conditions'] = []

    conditions = current['flash_conditions']
    existing = [r for r in conditions if r.get('id') == rule_data.get('id')]
    if existing:
        for i, r in enumerate(conditions):
            if r.get('id') == rule_data.get('id'):
                conditions[i] = rule_data
                break
    else:
        conditions.append(rule_data)

    return update_flash_guide_config(current)


def remove_flash_rule(rule_id):
    """
    删除一条闪光灯决策规则。

    参数：
        rule_id (str): 规则 ID。

    返回：
        dict: 更新后的完整配置，若规则不存在则返回当前配置。
    """
    current = get_flash_guide_config()
    conditions = current.get('flash_conditions', [])
    original_len = len(conditions)
    new_conditions = [r for r in conditions if r.get('id') != rule_id]
    if len(new_conditions) == original_len:
        if DEBUG:
            print("[Config] Flash rule with id '{}' not found".format(rule_id))
        return current
    current['flash_conditions'] = new_conditions
    return update_flash_guide_config(current)


def get_flash_rule(rule_id):
    """
    获取指定 ID 的闪光灯决策规则。

    参数：
        rule_id (str): 规则 ID。

    返回：
        dict: 规则数据，若不存在返回 None。
    """
    current = get_flash_guide_config()
    conditions = current.get('flash_conditions', [])
    for r in conditions:
        if r.get('id') == rule_id:
            return r
    return None


def list_flash_rules():
    """
    列出所有闪光灯决策规则。

    返回：
        list: 规则列表。
    """
    current = get_flash_guide_config()
    return current.get('flash_conditions', [])


def reset_flash_guide():
    """重置闪光灯配置为保守默认配置并保存到文件。"""
    global _cached_flash_guide
    default = _get_flash_conservative_default()
    _cached_flash_guide = default
    try:
        with open(FLASH_GUIDE_PATH, 'w') as f:
            json.dump(default, f)
        if DEBUG:
            print("[Config] Reset flash guide to conservative default")
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to reset flash guide: {}".format(e))
    return default


def _get_flash_conservative_default():
    """返回闪光灯极简保守默认配置（根级结构）。"""
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


# ==================== 重拍配置文件操作 ====================

def get_retry_guide_config(force_reload=False):
    """
    获取重拍指导配置。

    若 SD 卡配置文件不存在，返回极简保守配置。
    若文件存在，加载并缓存。

    参数：
        force_reload (bool): 是否强制重新从文件加载。

    返回：
        dict: 配置数据。
    """
    global _cached_retry_guide

    if _cached_retry_guide is not None and not force_reload:
        return _cached_retry_guide

    try:
        with open(RETRY_GUIDE_PATH, 'r') as f:
            _cached_retry_guide = json.load(f)
        if DEBUG:
            print("[Config] Loaded retry guide from {}".format(RETRY_GUIDE_PATH))
        return _cached_retry_guide
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to load retry guide: {}, using conservative default".format(e))
        _cached_retry_guide = _get_retry_conservative_default()
        return _cached_retry_guide


def update_retry_guide_config(new_config, save_to_file=True):
    """更新重拍指导配置（与现有配置合并）。"""
    global _cached_retry_guide
    current = get_retry_guide_config()
    merged = _deep_merge(current, new_config)
    _cached_retry_guide = merged
    if save_to_file:
        try:
            with open(RETRY_GUIDE_PATH, 'w') as f:
                json.dump(merged, f)
            if DEBUG:
                print("[Config] Saved retry guide to {}".format(RETRY_GUIDE_PATH))
        except Exception as e:
            if DEBUG:
                print("[Config] Failed to save retry guide: {}".format(e))
    return merged


def add_retry_rule(rule_data):
    """
    添加一条重拍决策规则到 retry_conditions 列表。

    参数：
        rule_data (dict): 规则数据，必须包含 'id', 'description', 'condition', 'action'。

    返回：
        dict: 更新后的完整配置。
    """
    current = get_retry_guide_config()
    if 'retry_conditions' not in current:
        current['retry_conditions'] = []

    conditions = current['retry_conditions']
    existing = [r for r in conditions if r.get('id') == rule_data.get('id')]
    if existing:
        for i, r in enumerate(conditions):
            if r.get('id') == rule_data.get('id'):
                conditions[i] = rule_data
                break
    else:
        conditions.append(rule_data)

    return update_retry_guide_config(current)


def remove_retry_rule(rule_id):
    """
    删除一条重拍决策规则。

    参数：
        rule_id (str): 规则 ID。

    返回：
        dict: 更新后的完整配置，若规则不存在则返回当前配置。
    """
    current = get_retry_guide_config()
    conditions = current.get('retry_conditions', [])
    original_len = len(conditions)
    new_conditions = [r for r in conditions if r.get('id') != rule_id]
    if len(new_conditions) == original_len:
        if DEBUG:
            print("[Config] Retry rule with id '{}' not found".format(rule_id))
        return current
    current['retry_conditions'] = new_conditions
    return update_retry_guide_config(current)


def get_retry_rule(rule_id):
    """
    获取指定 ID 的重拍决策规则。

    参数：
        rule_id (str): 规则 ID。

    返回：
        dict: 规则数据，若不存在返回 None。
    """
    current = get_retry_guide_config()
    conditions = current.get('retry_conditions', [])
    for r in conditions:
        if r.get('id') == rule_id:
            return r
    return None


def list_retry_rules():
    """
    列出所有重拍决策规则。

    返回：
        list: 规则列表。
    """
    current = get_retry_guide_config()
    return current.get('retry_conditions', [])


def reset_retry_guide():
    """重置重拍配置为保守默认配置并保存到文件。"""
    global _cached_retry_guide
    default = _get_retry_conservative_default()
    _cached_retry_guide = default
    try:
        with open(RETRY_GUIDE_PATH, 'w') as f:
            json.dump(default, f)
        if DEBUG:
            print("[Config] Reset retry guide to conservative default")
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to reset retry guide: {}".format(e))
    return default


def _get_retry_conservative_default():
    """返回重拍极简保守默认配置（仅亮度信息异常时重拍）。"""
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


# ==================== 通用工具函数 ====================

def _deep_merge(base, update):
    """深度合并字典。"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- config 模块测试 ---")
    print("\n1. 闪光灯配置:")
    flash_config = get_flash_guide_config()
    flash_rules = list_flash_rules()
    print("  闪光条件规则数:", len(flash_rules))
    for r in flash_rules:
        print("    - {}: {}".format(r.get('id'), r.get('description')))

    print("\n2. 重拍配置:")
    retry_config = get_retry_guide_config()
    retry_rules = list_retry_rules()
    print("  重拍条件规则数:", len(retry_rules))
    for r in retry_rules:
        print("    - {}: {}".format(r.get('id'), r.get('description')))