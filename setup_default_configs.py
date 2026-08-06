"""
setup_default_configs.py - 默认配置文件生成脚本

本脚本用于生成项目所需的默认配置文件，包括：
    1. flash_guide.json - 闪光灯智能决策规则配置

本脚本不会被其他模块调用，仅在首次部署或需要重置配置时手动执行。

用法：
    在 REPL 中执行：
    import setup_default_configs
    setup_default_configs.create_all()

    或单独创建：
    setup_default_configs.create_flash_guide()

设计原则：
    - 独立运行，不依赖其他模块（除了 config）
    - 生成完整、可用的默认配置
    - 提供详细的执行日志
"""
import json
import os
import time


def create_flash_guide(output_path="/sd/flash_guide.json", force=False):
    """
    创建默认的闪光灯指导配置文件。

    参数：
        output_path (str): 输出路径。
        force (bool): 是否强制覆盖已存在的文件。

    返回：
        bool: 创建成功返回 True。
    """
    print("[Setup] Creating flash guide config...")

    # 检查文件是否已存在
    try:
        with open(output_path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists at {}, use force=True to overwrite".format(output_path))
            return False
        print("[Setup] Overwriting existing file...")
    except:
        pass

    # 默认配置
    default_config = {
        "_comment": "闪光灯智能决策规则配置文件",
        "_version": "1.0.0",
        "_description": "根据环境亮度信息自动判断是否开启闪光灯及是否需要重拍",
        "_generated": time.time(),

        "rules": {
            "flash_decision": {
                "_comment": "闪光灯开启决策规则",
                "thresholds": {
                    "average_brightness": {
                        "_comment": "平均亮度阈值（0-255，数值越小越暗）",
                        "very_dark": 30,
                        "dark": 60,
                        "low": 100,
                        "normal": 150
                    },
                    "dynamic_range": {
                        "_comment": "动态范围阈值（最大灰度 - 最小灰度）",
                        "low_contrast": 50,
                        "medium_contrast": 100,
                        "high_contrast": 150
                    },
                    "center_brightness": {
                        "_comment": "中心区域亮度阈值（主体亮度）",
                        "dark_subject": 40,
                        "normal_subject": 80
                    }
                },
                "decision_logic": {
                    "_comment": "决策逻辑配置",
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
                    "retry_conditions": [
                        {
                            "id": "too_dark",
                            "description": "画面过暗：平均亮度 < 20",
                            "condition": "avg < 20",
                            "action": "retry_with_flash"
                        },
                        {
                            "id": "overexposed",
                            "description": "画面过曝：平均亮度 > 230",
                            "condition": "avg > 230",
                            "action": "retry_lower_exposure"
                        },
                        {
                            "id": "low_contrast",
                            "description": "对比度过低：动态范围 < 30 且 平均亮度 < 80",
                            "condition": "dynamic < 30 and avg < 80",
                            "action": "retry_adjust_settings"
                        }
                    ],
                    "default_action": {
                        "_comment": "默认行为（不满足任何条件时）",
                        "flash": "off",
                        "retry": False
                    }
                }
            }
        },

        "camera_settings": {
            "_comment": "不同场景下的推荐摄像头参数",
            "scene_profiles": {
                "normal": {
                    "description": "正常光照场景",
                    "brightness": 0,
                    "contrast": 0,
                    "saturation": 0,
                    "quality": 10
                },
                "dark": {
                    "description": "暗光场景（开启闪光灯）",
                    "brightness": 1,
                    "contrast": 1,
                    "saturation": 0,
                    "quality": 8
                },
                "very_dark": {
                    "description": "极暗场景（开启闪光灯 + 提高亮度）",
                    "brightness": 2,
                    "contrast": 1,
                    "saturation": -1,
                    "quality": 8
                },
                "backlit": {
                    "description": "逆光场景",
                    "brightness": 1,
                    "contrast": 2,
                    "saturation": 0,
                    "quality": 10
                }
            }
        },

        "logging": {
            "_comment": "日志配置",
            "enabled": True,
            "log_file": "/sd/flash_decision.log",
            "max_entries": 1000
        }
    }

    try:
        # 确保目录存在
        dir_path = os.path.dirname(output_path)
        if dir_path and not os.path.exists(dir_path):
            # MicroPython 可能不支持 os.makedirs，这里尝试创建
            pass

        with open(output_path, 'w') as f:
            json.dump(default_config, f, indent=4)

        print("[Setup] Flash guide config created at {}".format(output_path))
        print("[Setup] Version: {}".format(default_config['_version']))
        print("[Setup] Flash conditions: {} rules".format(
            len(default_config['rules']['flash_decision']['decision_logic']['flash_conditions'])))
        print("[Setup] Retry conditions: {} rules".format(
            len(default_config['rules']['flash_decision']['decision_logic']['retry_conditions'])))
        return True

    except Exception as e:
        print("[Setup] Failed to create flash guide: {}".format(e))
        return False


def create_all(output_dir="/sd", force=False):
    """
    创建所有默认配置文件。

    参数：
        output_dir (str): 输出目录。
        force (bool): 是否强制覆盖已存在的文件。

    返回：
        dict: 各文件创建结果。
    """
    print("\n" + "="*50)
    print("  创建默认配置文件")
    print("="*50)

    results = {
        'flash_guide': create_flash_guide(
            os.path.join(output_dir, "flash_guide.json"),
            force
        )
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

    # 询问是否覆盖
    import sys

    # 检查是否存在 flash_guide.json
    try:
        with open("flash_guide.json", 'r') as f:
            exists = True
    except:
        exists = False

    if exists:
        print("\n⚠️  flash_guide.json 已存在")
        response = input("是否覆盖？(y/N): ")
        if response.lower() != 'y':
            print("已取消")
            sys.exit(0)

    create_all(force=True)