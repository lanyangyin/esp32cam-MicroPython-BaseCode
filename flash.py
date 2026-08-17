"""
flash.py - 闪光灯控制模块（单例模式，支持 PWM 调光）

本模块提供 ESP32-CAM 板载闪光灯（GPIO 4）的 PWM 亮度控制功能。
采用单例模式管理闪光灯实例，确保全局只有一个控制对象。

核心功能：
    1. 单例管理：get_flash() 获取全局唯一实例，支持引脚和电平配置
    2. 亮度控制：set_brightness(value) 设置亮度 0~100 或 0.0~1.0
    3. 开关控制：on() 打开（最大亮度），off() 关闭（0亮度）
    4. 闪烁功能：blink(times, on_time, off_time) 闪烁指定次数
    5. 补光功能：pulse(duration) 短时点亮（用于拍照预闪）
    6. 重置功能：reset_flash() 释放并重置单例（释放 PWM 资源）

设计特点：
    - 使用 PWM 实现无级调光
    - 创建失败自动重试
    - 引脚和电平极性可配置（但 PWM 通常不考虑极性，以占空比控制）
    - 调试日志通过 config.DEBUG 控制

依赖关系：
    - machine.Pin, machine.PWM: GPIO 与 PWM 控制
    - config: 调试开关

典型用法：
    from flash import get_flash

    flash = get_flash(pin=4, on_value=1)
    flash.set_brightness(50)              # 设置 50% 亮度
    flash.on()                            # 最大亮度
    flash.off()                           # 关闭
    flash.blink(times=3, on_time=200, off_time=200)  # 以当前亮度闪烁
    flash.pulse(500)                      # 点亮 500ms
"""

import time
from machine import Pin, PWM
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Flash")


# ---------- 单例管理 ----------
_flash_instance = None


def get_flash(pin=4, on_value=1):
    """
    获取闪光灯单例对象。
    第一次调用时创建并初始化，后续调用返回同一实例。
    若创建失败，先尝试释放旧实例再重试。

    参数：
        pin (int): GPIO 引脚编号，默认 4（ESP32-CAM 板载 LED）。
        on_value (int): 此参数仅保持接口兼容，PWM 模式下忽略。

    返回：
        Flash: 单例实例。
    """
    global _flash_instance
    if _flash_instance is not None:
        _debug_log("Return existing flash instance")
        return _flash_instance

    _debug_log("Creating flash instance...")
    try:
        _flash_instance = Flash(pin, on_value)
        _debug_log("Flash created successfully")
        return _flash_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        if _flash_instance is not None:
            try:
                _flash_instance.off()
                del _flash_instance
                _flash_instance = None
            except:
                pass
        # 重试一次
        try:
            _flash_instance = Flash(pin, on_value)
            _debug_log("Flash created on retry")
            return _flash_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise


def reset_flash():
    """强制释放并重置闪光灯单例（释放 PWM 资源）。"""
    global _flash_instance
    if _flash_instance is not None:
        _debug_log("Resetting flash singleton")
        try:
            _flash_instance.deinit()
        except:
            pass
        _flash_instance = None


# ---------- Flash 类 ----------
class Flash:
    """
    ESP32-CAM 闪光灯控制类（PWM 调光）。
    支持亮度调节、开、关、闪烁、补光功能。
    """

    # PWM 频率（Hz），建议 1kHz 以上避免闪烁
    PWM_FREQ = 1000
    # 最大占空比（16位）
    DUTY_MAX = 65535

    def __init__(self, pin=4, on_value=1):
        """
        初始化闪光灯控制为 PWM 模式。

        参数：
            pin (int): GPIO 引脚编号，默认 4（ESP32-CAM 板载 LED）。
            on_value (int): 保持兼容，PWM 模式下忽略。
        """
        self._pin = Pin(pin, Pin.OUT)
        self._pwm = PWM(self._pin, freq=self.PWM_FREQ, duty_u16=0)
        self._brightness = 0  # 当前亮度百分比（0~100）
        _debug_log("Flash initialized on pin {} with PWM (freq={} Hz)".format(pin, self.PWM_FREQ))

    def set_brightness(self, value):
        """
        设置闪光灯亮度。

        参数：
            value (int/float): 亮度值，可以是 0~100 的整数，或 0.0~1.0 的浮点数。
                               value 会被限制在有效范围内。

        返回：
            float: 实际设置的亮度百分比（0~100）。
        """
        # 转换输入为百分比
        if isinstance(value, float):
            if 0.0 <= value <= 1.0:
                percent = value * 100.0
            else:
                percent = max(0.0, min(100.0, value))
        else:
            percent = max(0, min(100, int(value)))

        duty = int((percent / 100.0) * self.DUTY_MAX)
        self._pwm.duty_u16(duty)
        self._brightness = percent
        _debug_log("Brightness set to {:.1f}% (duty={})".format(percent, duty))
        return percent

    def on(self):
        """打开闪光灯（最大亮度）。"""
        self.set_brightness(100)
        _debug_log("Flash ON (max brightness)")

    def off(self):
        """关闭闪光灯（亮度 0）。"""
        self.set_brightness(0)
        _debug_log("Flash OFF")

    def blink(self, times=1, on_time=200, off_time=200):
        """
        闪烁指定次数（以当前亮度闪烁）。

        参数：
            times (int): 闪烁次数，默认 1。
            on_time (int): 开灯持续时间（毫秒），默认 200ms。
            off_time (int): 关灯后等待时间（毫秒），默认 200ms。
        """
        current_brightness = self._brightness
        _debug_log("Blinking {} times: ON {}ms, OFF {}ms (brightness {:.0f}%)".format(
            times, on_time, off_time, current_brightness))
        for _ in range(times):
            self.on()
            time.sleep_ms(on_time)
            self.off()
            time.sleep_ms(off_time)

    def pulse(self, duration=200):
        """
        短时补光（拍照预闪），点亮指定时间后自动关闭。

        参数：
            duration (int): 点亮持续时间（毫秒），默认 200ms。
        """
        _debug_log("Pulse for {} ms (brightness {:.0f}%)".format(duration, self._brightness))
        self.on()
        time.sleep_ms(duration)
        self.off()

    def deinit(self):
        """释放 PWM 资源（关闭并释放 Pin）。"""
        if hasattr(self, '_pwm') and self._pwm is not None:
            try:
                self._pwm.deinit()
            except:
                pass
            self._pwm = None
        if hasattr(self, '_pin') and self._pin is not None:
            try:
                self._pin.value(0)
            except:
                pass
        _debug_log("Flash deinitialized")


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import sys
    import gc

    print("\n--- Flash PWM 模块测试（带诊断） ---")
    start = time.ticks_ms()

    # 辅助诊断函数
    def check_flash(flash):
        if flash is None:
            print("❌ 闪光灯实例为 None")
            return False
        if not hasattr(flash, '_pwm') or flash._pwm is None:
            print("❌ PWM 对象丢失，尝试重新初始化...")
            try:
                flash._pwm = PWM(flash._pin, freq=flash.PWM_FREQ, duty_u16=0)
                print("✅ PWM 重新初始化成功")
                return True
            except Exception as e:
                print(f"❌ 重新初始化失败: {e}")
                return False
        try:
            duty = flash._pwm.duty_u16()
            print(f"当前占空比: {duty}")
            return True
        except Exception as e:
            print(f"❌ 读取 PWM 状态失败: {e}")
            return False

    # 测试创建单例
    f1 = get_flash()
    if check_flash(f1):
        print("✅ 闪光灯实例有效")
    else:
        print("❌ 闪光灯实例无效，退出测试")
        sys.exit(1)

    # 测试亮度渐变
    print("\n亮度渐变测试 (0% -> 100% -> 0%)...")
    for b in range(0, 101, 10):
        f1.set_brightness(b)
        time.sleep_ms(100)
        if b % 50 == 0:
            check_flash(f1)
    time.sleep_ms(200)
    for b in range(100, -1, -10):
        f1.set_brightness(b)
        time.sleep_ms(100)
        if b % 50 == 0:
            check_flash(f1)
    f1.off()
    time.sleep_ms(500)

    # 测试闪烁（3次）
    print("\n闪烁测试 (3次, 亮度50%)...")
    f1.set_brightness(50)
    f1.blink(times=3, on_time=200, off_time=200)
    time.sleep_ms(500)
    check_flash(f1)

    # 测试补光
    print("\n补光测试 (500ms, 亮度80%)...")
    f1.set_brightness(80)
    f1.pulse(500)
    check_flash(f1)

    # 测试重置
    print("\n重置并重新创建实例...")
    reset_flash()
    f3 = get_flash(pin=4, on_value=1)
    if check_flash(f3):
        print("✅ 新实例有效")
    else:
        print("❌ 新实例无效")

    # 最终清理
    if f3:
        f3.deinit()

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print(f"\n测试完成，耗时 {elapsed} ms")