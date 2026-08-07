# config/defaults.py
"""默认配置模板（保守）"""
def get_flash_conservative_default():
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

def get_retry_conservative_default():
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