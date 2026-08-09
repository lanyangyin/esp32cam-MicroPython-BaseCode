"""
indicator.py - 红色指示灯控制模块（单例模式）

ESP32-CAM 板载红色 LED（GPIO 33），低电平点亮。
提供开、关、闪烁、脉冲等控制功能。
"""
import time
from machine import Pin
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="Indicator")


# ---------- 单例管理 ----------
_indicator_instance = None


def get_indicator(pin=33, on_value=0, off_value=1):
    """
    获取指示灯单例对象。
    第一次调用时创建并初始化，后续返回同一实例。

    参数：
        pin (int): GPIO 引脚号，默认 33。
        on_value (int): 点亮电平，默认 0（低电平点亮）。
        off_value (int): 熄灭电平，默认 1（高电平熄灭）。
    """
    global _indicator_instance
    if _indicator_instance is not None:
        _debug_log("Return existing indicator instance")
        return _indicator_instance

    _debug_log("Creating indicator instance...")
    try:
        _indicator_instance = Indicator(pin, on_value, off_value)
        _debug_log("Indicator created successfully")
        return _indicator_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        # 重试一次
        try:
            _indicator_instance = Indicator(pin, on_value, off_value)
            _debug_log("Indicator created on retry")
            return _indicator_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise


def reset_indicator():
    """强制释放并重置指示灯单例"""
    global _indicator_instance
    if _indicator_instance is not None:
        _debug_log("Resetting indicator singleton")
        try:
            _indicator_instance.off()
        except:
            pass
        _indicator_instance = None


# ---------- Indicator 类 ----------
class Indicator:
    """
    红色指示灯控制类。
    默认 GPIO 33，低电平点亮。
    """

    def __init__(self, pin=33, on_value=0, off_value=1):
        """
        初始化指示灯。

        参数：
            pin (int): GPIO 引脚号，默认 33。
            on_value (int): 点亮电平，默认 0（低电平）。
            off_value (int): 熄灭电平，默认 1（高电平）。
        """
        self.pin = Pin(pin, Pin.OUT)
        self.on_value = on_value
        self.off_value = off_value
        self.off()
        _debug_log("Indicator initialized on pin {} (on_value={})".format(pin, on_value))

    def on(self):
        """点亮指示灯"""
        self.pin.value(self.on_value)
        _debug_log("Indicator ON")

    def off(self):
        """熄灭指示灯"""
        self.pin.value(self.off_value)
        _debug_log("Indicator OFF")

    def toggle(self):
        """翻转指示灯状态（简单翻转，注意电平极性）"""
        current = self.pin.value()
        # 如果当前是 on_value，则设为 off_value，反之亦然
        if current == self.on_value:
            self.pin.value(self.off_value)
        else:
            self.pin.value(self.on_value)
        _debug_log("Indicator toggled")

    def blink(self, times=3, on_time=200, off_time=200):
        """
        闪烁指定次数。

        参数：
            times (int): 闪烁次数。
            on_time (int): 亮灯持续时间（毫秒）。
            off_time (int): 灭灯持续时间（毫秒）。
        """
        _debug_log("Blinking {} times: ON {}ms, OFF {}ms".format(times, on_time, off_time))
        for _ in range(times):
            self.on()
            time.sleep_ms(on_time)
            self.off()
            time.sleep_ms(off_time)

    def pulse(self, duration=200):
        """
        短时点亮（脉冲），常用于指示事件。

        参数：
            duration (int): 点亮持续时间（毫秒）。
        """
        _debug_log("Pulse for {} ms".format(duration))
        self.on()
        time.sleep_ms(duration)
        self.off()


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("\n--- Indicator 模块测试 ---")
    led = get_indicator(pin=33, on_value=0, off_value=1)

    print("闪烁 3 次...")
    led.blink(times=3, on_time=200, off_time=200)
    time.sleep_ms(500)

    print("脉冲 500ms...")
    led.pulse(500)

    print("测试重置...")
    reset_indicator()
    led2 = get_indicator()
    print("重置后实例是否相同:", led2 is led)  # False，因为重置后旧实例释放，新创建

    print("测试完成")