"""
setup_default_configs.py - 默认配置文件生成脚本
"""
import json
import time
from config.camera_model import get_config_path, CAMERA_MODEL, get_camera_model

def create_flash_guide(force=False):
    path = get_config_path("flash_guide.json")
    print("[Setup] Creating flash guide config at {}".format(path))
    try:
        with open(path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists, use force=True to overwrite")
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
                "description": "逆光场景：RMS 对比度 > 40 且 平均亮度 < 100",
                "condition": "rms > 40 and avg < 100",
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
        with open(path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Flash guide config created")
        return True
    except Exception as e:
        print("[Setup] Failed to create flash guide: {}".format(e))
        return False

def create_retry_guide(force=False):
    path = get_config_path("retry_guide.json")
    print("[Setup] Creating retry guide config at {}".format(path))
    try:
        with open(path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists, use force=True to overwrite")
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
        with open(path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Retry guide config created")
        return True
    except Exception as e:
        print("[Setup] Failed to create retry guide: {}".format(e))
        return False

def create_quick_flash_guide(force=False):
    path = get_config_path("quick_flash_guide.json")
    print("[Setup] Creating quick flash guide config at {}".format(path))
    try:
        with open(path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists, use force=True to overwrite")
            return False
        print("[Setup] Overwriting existing file...")
    except:
        pass

    config = {
        "_comment": "快速闪光灯决策配置（基于平均亮度阈值）",
        "_version": "1.0.0",
        "_description": "当平均亮度低于 threshold 时开启闪光灯",
        "_generated": time.time(),
        "threshold": 30,
        "default_action": "off"
    }

    try:
        with open(path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Quick flash guide config created")
        return True
    except Exception as e:
        print("[Setup] Failed to create quick flash guide: {}".format(e))
        return False

def create_black_photo_config(force=False):
    path = get_config_path("black_photo_config.json")
    print("[Setup] Creating black photo config at {}".format(path))
    try:
        with open(path, 'r') as f:
            existing = json.load(f)
        if not force:
            print("[Setup] File already exists, use force=True to overwrite")
            return False
        print("[Setup] Overwriting existing file...")
    except:
        pass

    config = {
        "_comment": "黑照检测阈值配置（各分辨率下的最小照片大小，单位为字节）",
        "_version": "1.0.0",
        "_description": "如果 JPEG 大小低于该值，视为黑照，需要重试",
        "_generated": time.time(),
        "_model": "ov3660",
        "FRAME_96X96": 807,
        "FRAME_QQVGA": 1002,
        "FRAME_QCIF": 1122,
        "FRAME_HQVGA": 1452,
        "FRAME_240X240": 1752,
        "FRAME_QVGA": 2165,
        "FRAME_CIF": 2998,
        "FRAME_HVGA": 5531,
        "FRAME_VGA": 7291,
        "FRAME_SVGA": 11092,
        "FRAME_XGA": 16155,
        "FRAME_HD": 18627,
        "FRAME_SXGA": 26227,
        "FRAME_UXGA": 39143,
        "FRAME_FHD": 41127,
        "FRAME_P_HD": 18634,
        "FRAME_P_3MP": 26547,
        "FRAME_QXGA": 62942,
    }

    try:
        with open(path, 'w') as f:
            json.dump(config, f)
        print("[Setup] Black photo config created")
        return True
    except Exception as e:
        print("[Setup] Failed to create black photo config: {}".format(e))
        return False

def create_all(force=False):
    print("\n" + "="*50)
    print("  创建默认配置文件 (型号: {})".format(get_camera_model()))
    print("="*50)
    results = {
        'flash_guide': create_flash_guide(force),
        'retry_guide': create_retry_guide(force),
        'quick_flash_guide': create_quick_flash_guide(force),
        'black_photo_config': create_black_photo_config(force),
    }
    print("\n" + "="*50)
    print("  创建完成")
    print("="*50)
    for name, success in results.items():
        print("  {}: {}".format(name, "✅ 成功" if success else "⏭️  跳过/失败"))
    return results

if __name__ == "__main__":
    create_all(force=True)