"""
flash_decision.py - 智能闪光灯决策模块

本模块根据环境亮度信息和闪光灯指导配置文件（flash_guide.json），
自动判断是否需要开启闪光灯以及是否需要重拍。

核心功能：
    1. load_flash_guide(): 加载闪光灯指导配置文件
    2. evaluate_flash_decision(): 根据亮度信息评估决策
    3. should_use_flash(): 快速判断是否开启闪光灯
    4. should_retry(): 快速判断是否需要重拍

设计原则：
    - 决策逻辑与硬件控制分离
    - 配置文件驱动，便于调整阈值
    - 支持多种决策条件组合
    - 使用 config 模块的保守默认配置（内存优化）

依赖关系：
    - config: 配置文件操作（增删改查）
    - utils: 亮度分析函数

典型用法：
    from flash_decision import should_use_flash, should_retry

    brightness_info = {
        'average_brightness': 45.0,
        'dynamic_range': 80,
        'center_brightness': 35.0
    }

    if should_use_flash(brightness_info):
        print("需要开启闪光灯")
        # 开启闪光灯拍照
    else:
        print("无需闪光灯")
        # 正常拍照

    if should_retry(brightness_info):
        print("需要重拍")
"""
import json
import os
from config import get_flash_guide_config, update_flash_guide_config
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

    优先从 SD 卡加载，若失败则使用 config 模块的保守默认配置。

    参数：
        guide_path (str): 配置文件路径，默认 /sd/flash_guide.json

    返回：
        dict: 配置数据。
    """
    global _cached_guide

    if _cached_guide is not None:
        return _cached_guide

    # 直接从 config 获取（自动处理文件不存在的情况）
    try:
        _cached_guide = get_flash_guide_config()
        _debug_log("Loaded flash guide via config module")
        return _cached_guide
    except Exception as e:
        _debug_log("Failed to load via config: {}, using minimal default".format(e))
        _cached_guide = _get_minimal_default()
        return _cached_guide


def reload_flash_guide(guide_path=DEFAULT_GUIDE_PATH):
    """强制重新加载配置文件。"""
    global _cached_guide
    _cached_guide = None
    return load_flash_guide(guide_path)


def _get_minimal_default():
    """
    极简默认配置（当 config 模块也无法提供时使用）。

    这个配置只用于应急，正常情况下不会用到。
    """
    return {
        "rules": {
            "flash_decision": {
                "decision_logic": {
                    "flash_conditions": [],
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
    根据亮度信息评估闪光灯决策。

    返回：
        dict: 包含 flash, retry, 推荐场景配置等。
    """
    guide = load_flash_guide(guide_path)
    rules = guide.get('rules', {}).get('flash_decision', {})
    decision_logic = rules.get('decision_logic', {})
    flash_conditions = decision_logic.get('flash_conditions', [])
    retry_conditions = decision_logic.get('retry_conditions', [])
    default_action = decision_logic.get('default_action', {})

    result = {
        'flash': False,
        'retry': False,
        'retry_reason': '',
        'flash_reason': '',
        'matched_rule': '',
        'scene_profile': 'normal',
        'all_results': []
    }

    # 检查闪光灯条件
    for cond in flash_conditions:
        cond_str = cond.get('condition', '')
        if _evaluate_condition(cond_str, brightness_info):
            result['flash'] = True
            result['flash_reason'] = cond.get('description', '')
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
        result['scene_profile'] = 'normal'

    # 检查重拍条件
    for cond in retry_conditions:
        cond_str = cond.get('condition', '')
        if _evaluate_condition(cond_str, brightness_info):
            result['retry'] = True
            result['retry_reason'] = cond.get('description', '')
            result['matched_rule'] = cond.get('id', '')
            if cond.get('action') == 'retry_with_flash':
                result['flash'] = True
            break

    # 记录所有条件评估结果（用于调试）
    result['all_results'] = []
    for cond in flash_conditions:
        result['all_results'].append({
            'id': cond.get('id', ''),
            'description': cond.get('description', ''),
            'condition': cond.get('condition', ''),
            'matched': _evaluate_condition(cond.get('condition', ''), brightness_info)
        })

    _debug_log("Decision: flash={}, retry={}, profile={}".format(
        result['flash'], result['retry'], result['scene_profile']))

    return result


def should_use_flash(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    """快速判断是否开启闪光灯。"""
    result = evaluate_flash_decision(brightness_info, guide_path)
    return result.get('flash', False)


def should_retry(brightness_info, guide_path=DEFAULT_GUIDE_PATH):
    """快速判断是否需要重拍。"""
    result = evaluate_flash_decision(brightness_info, guide_path)
    return result.get('retry', False)


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
    import time
    import gc

    print("\n" + "="*50)
    print("  flash_decision 模块测试")
    print("="*50)

    # ========== 1. 使用模拟图片测试决策（逐个生成并释放） ==========
    print("\n--- 1. 模拟图片测试（无硬件依赖） ---")
    from utils import (
        create_uniform_image, create_gradient_image,
        create_center_bright_image, create_center_dark_image,
        analyze_brightness
    )

    test_width, test_height = 160, 120  # 用较小尺寸加速

    # 定义场景 (名称, 生成函数, 参数字典)
    scenarios = [
        ("极暗（全黑）", create_uniform_image, {'value': 5}),
        ("暗（均匀灰）", create_uniform_image, {'value': 40}),
        ("中灰", create_uniform_image, {'value': 128}),
        ("亮（均匀灰）", create_uniform_image, {'value': 200}),
        ("极亮（全白）", create_uniform_image, {'value': 250}),
        ("渐变（水平）", create_gradient_image, {'direction': 'horizontal'}),
        ("中心亮（聚光）", create_center_bright_image, {'center_radius_ratio': 0.25, 'center_value': 220, 'surround_value': 30}),
        ("中心暗（逆光）", create_center_dark_image, {'center_radius_ratio': 0.25, 'center_value': 30, 'surround_value': 220}),
    ]

    print("  {:^20} | {:^8} | {:^8} | {:^6} | {:^6}".format(
        "场景", "平均亮度", "动态范围", "闪光灯", "重拍"))
    print("  " + "-"*60)

    for name, gen_func, kwargs in scenarios:
        img_data = gen_func(test_width, test_height, **kwargs)
        result = analyze_brightness(img_data, test_width, test_height, step=2)
        if result:
            decision = evaluate_flash_decision({
                'average_brightness': result['average_brightness'],
                'dynamic_range': result['dynamic_range'],
                'center_brightness': result['center_brightness']
            })
            print("  {:^20} | {:8.1f} | {:8} | {:^6} | {:^6}".format(
                name[:20],
                result['average_brightness'],
                result['dynamic_range'],
                "✅" if decision['flash'] else "❌",
                "✅" if decision['retry'] else "❌"
            ))
        # 释放
        del img_data
        gc.collect()

    # ========== 2. 使用预设测试用例 ==========
    print("\n--- 2. 预设测试用例 ---")
    test_cases = [
        {"average_brightness": 15.0, "dynamic_range": 20, "center_brightness": 10.0},
        {"average_brightness": 45.0, "dynamic_range": 80, "center_brightness": 35.0},
        {"average_brightness": 75.0, "dynamic_range": 120, "center_brightness": 45.0},
        {"average_brightness": 120.0, "dynamic_range": 50, "center_brightness": 110.0},
        {"average_brightness": 200.0, "dynamic_range": 30, "center_brightness": 190.0},
        {"average_brightness": 60.0, "dynamic_range": 20, "center_brightness": 55.0},
    ]

    print("  {:^10} | {:^8} | {:^8} | {:^6} | {:^6} | {:^12}".format(
        "avg", "dynamic", "center", "闪光", "重拍", "场景配置"))
    print("  " + "-"*65)

    for info in test_cases:
        result = evaluate_flash_decision(info)
        print("  {:>10} | {:>8} | {:>8} | {:^6} | {:^6} | {:^12}".format(
            info['average_brightness'],
            info['dynamic_range'],
            info['center_brightness'],
            "✅" if result['flash'] else "❌",
            "✅" if result['retry'] else "❌",
            result['scene_profile']
        ))

    # ========== 3. 从 SD 卡加载图片测试 ==========
    print("\n--- 3. SD 卡图片测试（如果存在） ---")
    try:
        import uos
        from utils import load_image_from_file, get_image_info

        files = uos.listdir('/sd')
        jpg_files = [f for f in files if f.lower().endswith('.jpg') or f.lower().endswith('.jpeg')]
        if jpg_files:
            test_file = '/sd/' + jpg_files[0]
            print("  加载文件: {}".format(test_file))
            img_data = load_image_from_file(test_file)
            if img_data:
                info = get_image_info(img_data)
                print("  文件信息: 格式={}, 大小={} bytes, 尺寸={}x{}".format(
                    info['format'], info['size_bytes'], info['width'], info['height']))
                # 注意：JPEG 是压缩格式，无法直接用于亮度分析
                print("  ⚠️ JPEG 是压缩格式，无法直接分析亮度（需要解码）")
                print("  提示: 使用 utils.create_* 生成的图片已覆盖测试场景")
                del img_data
                gc.collect()
            else:
                print("  ❌ 加载失败")
        else:
            print("  ⚠️ 未找到 JPEG 文件，跳过")
    except Exception as e:
        print("  ⚠️ SD 卡读取失败: {}".format(e))

    print("\n" + "="*50)
    print("  测试完成")
    print("="*50)