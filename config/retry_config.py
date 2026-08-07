# config/retry_config.py
"""重拍配置文件操作"""
import json
from .debug import DEBUG
from .defaults import get_retry_conservative_default

RETRY_GUIDE_PATH = "/sd/retry_guide.json"
_cached_retry_guide = None

def _deep_merge(base, update):
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def get_retry_guide_config(force_reload=False):
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
        _cached_retry_guide = get_retry_conservative_default()
        return _cached_retry_guide

def update_retry_guide_config(new_config, save_to_file=True):
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
    current = get_retry_guide_config()
    conditions = current.get('retry_conditions', [])
    new_conditions = [r for r in conditions if r.get('id') != rule_id]
    if len(new_conditions) == len(conditions):
        if DEBUG:
            print("[Config] Retry rule with id '{}' not found".format(rule_id))
        return current
    current['retry_conditions'] = new_conditions
    return update_retry_guide_config(current)

def get_retry_rule(rule_id):
    current = get_retry_guide_config()
    for r in current.get('retry_conditions', []):
        if r.get('id') == rule_id:
            return r
    return None

def list_retry_rules():
    return get_retry_guide_config().get('retry_conditions', [])

def reset_retry_guide():
    global _cached_retry_guide
    default = get_retry_conservative_default()
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