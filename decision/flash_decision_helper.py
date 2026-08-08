# decision/flash_decision_helper.py
"""
闪光灯决策辅助工具（交互式）
捕获灰度图，显示亮度信息和当前决策，让用户逐步修正规则。
"""
import camera
from config import debug_log, LEVEL_INFO
from camera_driver import capture_grayscale, CameraController, reset_camera
from config.flash_config import FLASH_GUIDE_PATH
from utils.brightness import analyze_brightness
from .flash import load_flash_guide, reload_flash_guide, evaluate_flash_decision
from .retry import should_retry, get_retry_reason


def _get_brightness_info(framesize=camera.FRAME_QVGA):
    """捕获灰度图并分析亮度信息（单次）"""
    reset_camera()
    gray = capture_grayscale(framesize=framesize, whitebalance=camera.WB_CLOUDY)
    if gray is None:
        return None
    w, h = CameraController.get_resolution(framesize)
    if w is None or h is None:
        total = len(gray)
        w = int((total * 4 / 3) ** 0.5)
        h = total // w
        if w * h != total:
            w, h = 320, 240
    return analyze_brightness(gray, w, h, step=2)


def _show_info(brightness_info):
    """打印亮度信息"""
    print("\n亮度信息:")
    print(f"  平均亮度 (avg)       : {brightness_info['average_brightness']:.1f}")
    print(f"  RMS 对比度 (rms)     : {brightness_info['rms_contrast']:.1f}")
    print(f"  中心亮度 (center)    : {brightness_info['center_brightness']:.1f}")
    print(f"  动态范围 (dynamic)   : {brightness_info['dynamic_range']:.1f}")


def _show_decision(brightness_info):
    """显示当前决策"""
    result = evaluate_flash_decision(brightness_info)
    print("\n当前决策:")
    print(f"  开闪光灯? {result['flash']}")
    if result['matched_rule']:
        print(f"  匹配规则: {result['matched_rule']} - {result['reason']}")
    else:
        print("  未匹配任何规则，使用默认动作")
    print(f"  场景分类: {result['scene_profile']}")
    return result


def flash_decision_helper(framesize=camera.FRAME_QVGA):
    """
    交互式辅助：捕获亮度、显示决策，并让用户修改规则。
    如果捕获的亮度信息满足重拍条件，会自动重试直到有效。
    """
    print("\n" + "="*60)
    print("闪光灯决策辅助工具")
    print("="*60)

    MAX_RETRIES = 6

    # 获取有效的亮度信息
    info = None
    for attempt in range(1, MAX_RETRIES + 1):
        info = _get_brightness_info(framesize)
        if info is None:
            print("❌ 无法捕获灰度图，请检查摄像头")
            return
        if should_retry(info):
            reason = get_retry_reason(info)
            print(f"⚠️ 亮度信息异常 (尝试 {attempt}/{MAX_RETRIES}): {reason}")
            continue
        else:
            break
    else:
        if info is not None:
            print("⚠️ 已达到最大重试次数，使用最后一次亮度信息（可能不准确）")
        else:
            print("❌ 无法获取有效亮度信息")
            return

    _show_info(info)
    result = _show_decision(info)

    # 交互循环
    while True:
        print("\n这个决策正确吗？ (y/n/q=退出)")
        ans = input("> ").strip().lower()
        if ans == 'y':
            print("✅ 决策正确，无需修改")
            break
        elif ans == 'q':
            print("退出")
            break
        elif ans == 'n':
            _modify_rules(info)
            reload_flash_guide()
            # 重新获取有效的亮度信息
            for attempt in range(1, MAX_RETRIES + 1):
                info = _get_brightness_info(framesize)
                if info is None:
                    print("❌ 重新捕获失败")
                    break
                if should_retry(info):
                    reason = get_retry_reason(info)
                    print(f"⚠️ 亮度信息异常 (尝试 {attempt}/{MAX_RETRIES}): {reason}")
                    continue
                else:
                    break
            if info is None:
                print("❌ 无法获取有效亮度信息，退出")
                break
            _show_info(info)
            _show_decision(info)
        else:
            print("请输入 y/n/q")


def _modify_rules(brightness_info):
    """交互式修改规则"""
    guide = load_flash_guide()
    conditions = guide.get('flash_conditions', [])
    if not conditions:
        print("没有可修改的规则，请先创建规则")
        return

    print("\n当前规则列表:")
    for i, cond in enumerate(conditions):
        print(f"  {i+1}. {cond.get('id')} : {cond.get('description')}")
        print(f"     条件: {cond.get('condition')} -> 动作: {cond.get('action')}")

    print("\n选择要修改的规则编号 (或输入 'add' 添加新规则, 'del' 删除规则, 'q' 取消):")
    choice = input("> ").strip().lower()

    if choice == 'q':
        return
    elif choice == 'add':
        _add_rule(guide)
    elif choice == 'del':
        _delete_rule(guide)
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(conditions):
                _edit_rule(conditions[idx], guide)
            else:
                print("无效编号")
        except ValueError:
            print("无效输入")


def _edit_rule(cond, guide):
    """编辑单条规则的条件"""
    print(f"\n编辑规则: {cond.get('id')}")
    print(f"当前条件: {cond.get('condition')}")
    print("你可以修改条件中的数值（如 avg, rms, center, dynamic）")
    print("示例: 'avg < 30' 修改为 'avg < 25'")
    new_cond = input("输入新条件 (留空保持原样): ").strip()
    if new_cond:
        if any(v in new_cond for v in ['avg', 'rms', 'center', 'dynamic']):
            cond['condition'] = new_cond
            guide['flash_conditions'] = [c for c in guide['flash_conditions'] if c.get('id') != cond['id']] + [cond]
            _save_guide(guide)
            print("✅ 规则已更新")
        else:
            print("❌ 条件必须包含 avg, rms, center 或 dynamic 变量")


def _add_rule(guide):
    """添加新规则"""
    print("\n添加新规则")
    rule_id = input("规则ID (例如 my_rule): ").strip()
    if not rule_id:
        print("ID不能为空")
        return
    description = input("描述: ").strip()
    condition = input("条件 (例如 avg < 20): ").strip()
    action = input("动作 (flash_on 或 flash_off): ").strip()
    if not condition or not action:
        print("条件和动作不能为空")
        return
    new_rule = {
        "id": rule_id,
        "description": description,
        "condition": condition,
        "action": action
    }
    guide['flash_conditions'].append(new_rule)
    _save_guide(guide)
    print("✅ 规则已添加")


def _delete_rule(guide):
    """删除规则"""
    print("\n删除规则")
    rule_id = input("输入要删除的规则ID: ").strip()
    if not rule_id:
        return
    original_len = len(guide['flash_conditions'])
    guide['flash_conditions'] = [c for c in guide['flash_conditions'] if c.get('id') != rule_id]
    if len(guide['flash_conditions']) < original_len:
        _save_guide(guide)
        print("✅ 规则已删除")
    else:
        print("未找到该ID")


def _save_guide(guide):
    """保存配置文件并重新加载"""
    import json
    try:
        with open(FLASH_GUIDE_PATH, 'w') as f:
            json.dump(guide, f)
        reload_flash_guide()
        print("✅ 配置已保存并重新加载")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    from config import set_debug
    set_debug(True)
    flash_decision_helper(framesize=camera.FRAME_QVGA)