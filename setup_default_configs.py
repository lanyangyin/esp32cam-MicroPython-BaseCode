"""
setup_default_configs.py - 默认配置文件生成脚本

本脚本用于生成项目所需的默认配置文件，包括：
    1. flash_guide.json - 闪光灯决策规则
    2. retry_guide.json - 重拍决策规则（重新获取亮度信息）

本脚本不会被其他模块调用，仅在首次部署或需要重置配置时手动执行。

用法：
    在 REPL 中执行：
    import setup_default_configs
    setup_default_configs.create_all()

    或单独创建：
    setup_default_configs.create_flash_guide()
    setup_default_configs.create_retry_guide()
"""
import json
import time


def create_flash_guide(output_path="/sd/flash_guide.json", force=False):
    """创建默认的闪光灯决策配置文件。"""
    print("[Setup] Creating flash guide config...")

    try:
        with open(output_path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists at {}, use force=True to overwrite".format(output_path))
            return False
        print("[Setup] Overwriting existing file...")
    except:
        pass

    config = {
        "_comment": "闪光灯决策规则配置文件",
        "_version": "1.0.0",
        "_description": "根据环境亮度信息自动判断是否开启闪光灯",
        "_generated": time.time(),

        "flash_conditions": [
            {
                "id": "very_dark_scene",
                "description": "场景极暗：平均亮度 < 30",
                "condition": "avg < 30",
                "action": "flash_on"
            },
            {
                "id": "dark_scene",
                "description": "场景较暗：平均亮度 < 60 且 中心亮度 < 40",
                "condition": "avg < 60 and center < 40",
                "action": "flash_on"
            },
            {
                "id": "dark_subject",
                "description": "主体偏暗：平均亮度 < 80 且 中心亮度 < 50",
                "condition": "avg < 80 and center < 50",
                "action": "flash_on"
            },
            {
                "id": "backlit_scene",
                "description": "逆光场景：动态范围 > 100 且 平均亮度 < 100",
                "condition": "dynamic > 100 and avg < 100",
                "action": "flash_on"
            }
        ],
        "default_action": {"flash": "off"},
        "camera_settings": {
            "scene_profiles": {
                "normal": {"brightness": 0, "contrast": 0, "saturation": 0, "quality": 10},
                "dark": {"brightness": 1, "contrast": 1, "saturation": 0, "quality": 8},
                "very_dark": {"brightness": 2, "contrast": 1, "saturation": -1, "quality": 8},
                "backlit": {"brightness": 1, "contrast": 2, "saturation": 0, "quality": 10}
            }
        }
    }

    try:
        with open(output_path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Flash guide config created at {}".format(output_path))
        print("[Setup] Flash conditions: {} rules".format(len(config['flash_conditions'])))
        return True
    except Exception as e:
        print("[Setup] Failed to create flash guide: {}".format(e))
        return False


def create_retry_guide(output_path="/sd/retry_guide.json", force=False):
    """创建默认的重拍决策配置文件（仅保留亮度信息异常检测）。"""
    print("[Setup] Creating retry guide config...")

    try:
        with open(output_path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists at {}, use force=True to overwrite".format(output_path))
            return False
        print("[Setup] Overwriting existing file...")
    except:
        pass

    config = {
        "_comment": "重拍决策规则配置文件（重新获取亮度信息）",
        "_version": "1.0.0",
        "_description": "根据环境亮度信息自动判断是否需要重新获取亮度信息",
        "_generated": time.time(),

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

    try:
        with open(output_path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Retry guide config created at {}".format(output_path))
        print("[Setup] Retry conditions: {} rules".format(len(config['retry_conditions'])))
        return True
    except Exception as e:
        print("[Setup] Failed to create retry guide: {}".format(e))
        return False


def create_all(output_dir="/sd", force=False):
    """创建所有默认配置文件。"""
    print("\n" + "="*50)
    print("  创建默认配置文件")
    print("="*50)

    flash_guide_path = output_dir + "/flash_guide.json" if output_dir else "flash_guide.json"
    retry_guide_path = output_dir + "/retry_guide.json" if output_dir else "retry_guide.json"

    results = {
        'flash_guide': create_flash_guide(flash_guide_path, force),
        'retry_guide': create_retry_guide(retry_guide_path, force)
    }

    print("\n" + "="*50)
    print("  创建完成")
    print("="*50)
    for name, success in results.items():
        print("  {}: {}".format(name, "✅ 成功" if success else "⏭️  跳过/失败"))

    return results


# ---------- 独立运行入口 ----------
if __name__ == "__main__":
    print("\n--- 默认配置文件生成工具 ---")
    print("本脚本将生成项目所需的默认配置文件。")

    import sys

    # 检查文件是否存在
    flash_exists = False
    retry_exists = False
    try:
        with open("/sd/flash_guide.json", 'r') as f:
            flash_exists = True
    except:
        pass
    try:
        with open("/sd/retry_guide.json", 'r') as f:
            retry_exists = True
    except:
        pass

    if flash_exists or retry_exists:
        print("\n⚠️  以下文件已存在:")
        if flash_exists:
            print("  - /sd/flash_guide.json")
        if retry_exists:
            print("  - /sd/retry_guide.json")


    create_all(force=True)