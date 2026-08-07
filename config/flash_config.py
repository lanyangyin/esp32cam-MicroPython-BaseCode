# config/flash_config.py
"""闪光灯配置文件操作"""
import json
from .debug import DEBUG
from .defaults import get_flash_conservative_default

FLASH_GUIDE_PATH = "/sd/flash_guide.json"
_cached_flash_guide = None

def _deep_merge(base, update):
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def get_flash_guide_config(force_reload=False):
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
        _cached_flash_guide = get_flash_conservative_default()
        return _cached_flash_guide

def update_flash_guide_config(new_config, save_to_file=True):
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
    current = get_flash_guide_config()
    conditions = current.get('flash_conditions', [])
    new_conditions = [r for r in conditions if r.get('id') != rule_id]
    if len(new_conditions) == len(conditions):
        if DEBUG:
            print("[Config] Flash rule with id '{}' not found".format(rule_id))
        return current
    current['flash_conditions'] = new_conditions
    return update_flash_guide_config(current)

def get_flash_rule(rule_id):
    current = get_flash_guide_config()
    for r in current.get('flash_conditions', []):
        if r.get('id') == rule_id:
            return r
    return None

def list_flash_rules():
    return get_flash_guide_config().get('flash_conditions', [])

def reset_flash_guide():
    global _cached_flash_guide
    default = get_flash_conservative_default()
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