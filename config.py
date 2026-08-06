"""
config.py - 全局配置模块

本文件提供项目的全局配置变量和函数，目前主要用于调试日志的控制。
所有模块通过 from config import DEBUG 共享同一个调试开关。

扩展功能：
    - 闪光灯指导配置文件（flash_guide.json）的增删改查操作
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
    from config import get_flash_guide_config, update_flash_guide_config
    config = get_flash_guide_config()
    update_flash_guide_config({"rules": {...}})
"""
import json
import os

# 全局调试开关，所有模块共享
DEBUG = True

# 闪光灯配置文件路径
FLASH_GUIDE_PATH = "/sd/flash_guide.json"

# 缓存配置
_cached_flash_guide = None


def set_debug(enabled):
    """设置调试模式（True 启用日志，False 关闭）。"""
    global DEBUG
    DEBUG = enabled


# ========== 闪光灯配置文件操作 ==========

def get_flash_guide_config(force_reload=False):
    """
    获取闪光灯指导配置。

    若 SD 卡配置文件不存在，返回极简保守配置（不闪光、不重拍）。
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
        _cached_flash_guide = _get_conservative_default()
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
                json.dump(merged, f)  # 移除 indent=4
            if DEBUG:
                print("[Config] Saved flash guide to {}".format(FLASH_GUIDE_PATH))
        except Exception as e:
            if DEBUG:
                print("[Config] Failed to save flash guide: {}".format(e))
    return merged


def reset_flash_guide():
    global _cached_flash_guide
    default = _get_conservative_default()
    _cached_flash_guide = default
    try:
        with open(FLASH_GUIDE_PATH, 'w') as f:
            json.dump(default, f)  # 移除 indent=4
        if DEBUG:
            print("[Config] Reset flash guide to conservative default")
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to reset flash guide: {}".format(e))
    return default


def add_flash_rule(rule_type, rule_data):
    """添加闪光灯决策规则（同前）。"""
    current = get_flash_guide_config()
    rules = current.get('rules', {}).get('flash_decision', {})
    decision_logic = rules.get('decision_logic', {})
    if rule_type not in decision_logic:
        decision_logic[rule_type] = []
    existing = [r for r in decision_logic[rule_type] if r.get('id') == rule_data.get('id')]
    if existing:
        for i, r in enumerate(decision_logic[rule_type]):
            if r.get('id') == rule_data.get('id'):
                decision_logic[rule_type][i] = rule_data
                break
    else:
        decision_logic[rule_type].append(rule_data)
    current['rules']['flash_decision']['decision_logic'] = decision_logic
    return update_flash_guide_config(current)


def remove_flash_rule(rule_type, rule_id):
    """删除闪光灯决策规则。"""
    current = get_flash_guide_config()
    rules = current.get('rules', {}).get('flash_decision', {})
    decision_logic = rules.get('decision_logic', {})
    if rule_type not in decision_logic:
        return current
    decision_logic[rule_type] = [r for r in decision_logic[rule_type] if r.get('id') != rule_id]
    current['rules']['flash_decision']['decision_logic'] = decision_logic
    return update_flash_guide_config(current)


def get_flash_rule(rule_type, rule_id):
    """获取指定规则。"""
    current = get_flash_guide_config()
    rules = current.get('rules', {}).get('flash_decision', {})
    decision_logic = rules.get('decision_logic', {})
    if rule_type not in decision_logic:
        return None
    for r in decision_logic[rule_type]:
        if r.get('id') == rule_id:
            return r
    return None


def list_flash_rules(rule_type=None):
    """列出所有规则。"""
    current = get_flash_guide_config()
    rules = current.get('rules', {}).get('flash_decision', {})
    decision_logic = rules.get('decision_logic', {})
    result = {}
    if rule_type is None or rule_type == 'flash_conditions':
        result['flash_conditions'] = decision_logic.get('flash_conditions', [])
    if rule_type is None or rule_type == 'retry_conditions':
        result['retry_conditions'] = decision_logic.get('retry_conditions', [])
    return result


def reset_flash_guide():
    """重置为保守默认配置并保存到文件。"""
    global _cached_flash_guide
    default = _get_conservative_default()
    _cached_flash_guide = default
    try:
        with open(FLASH_GUIDE_PATH, 'w') as f:
            json.dump(default, f, indent=4)
        if DEBUG:
            print("[Config] Reset flash guide to conservative default")
    except Exception as e:
        if DEBUG:
            print("[Config] Failed to reset flash guide: {}".format(e))
    return default


def _get_conservative_default():
    """
    返回极简保守默认配置（内存友好）。

    仅包含最必要的规则，确保在无配置文件时也能正常决策：
    - 仅当平均亮度 < 20 时才开启闪光灯（极暗场景）
    - 不触发重拍（保守策略）
    - 默认不闪光
    """
    return {
        "rules": {
            "flash_decision": {
                "thresholds": {
                    "average_brightness": {
                        "very_dark": 20,
                    },
                    "dynamic_range": {},
                    "center_brightness": {}
                },
                "decision_logic": {
                    "flash_conditions": [
                        {
                            "id": "conservative_very_dark",
                            "description": "极暗场景（保守）",
                            "condition": "avg < 20",
                            "action": "flash_on"
                        }
                    ],
                    "retry_conditions": [],
                    "default_action": {"flash": "off", "retry": False}
                }
            }
        },
        "camera_settings": {
            "scene_profiles": {
                "normal": {"brightness": 0, "contrast": 0, "saturation": 0, "quality": 10}
            }
        }
    }


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
    config = get_flash_guide_config()
    rules = list_flash_rules()
    print("闪光条件规则数:", len(rules.get('flash_conditions', [])))
    print("重拍条件规则数:", len(rules.get('retry_conditions', [])))