# flash.py
from machine import Pin
import time
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[Flash] " + msg)

# ---------- 单例管理 ----------
_flash_instance = None

def get_flash(pin=4, on_value=1):
    """
    获取闪光灯单例对象。
    第一次调用时创建并初始化，后续调用返回同一实例。
    若创建失败，先尝试释放旧实例再重试。

    参数：
        pin (int): GPIO 引脚编号，默认 4。
        on_value (int): 点亮电平，1 高电平，0 低电平，默认 1。

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
    """强制释放并重置闪光灯单例（用于调试或重新配置）。"""
    global _flash_instance
    if _flash_instance is not None:
        _debug_log("Resetting flash singleton")
        try:
            _flash_instance.off()
        except:
            pass
        _flash_instance = None

# ---------- Flash 类 ----------
class Flash:
    """
    ESP32-CAM 闪光灯控制类。
    支持设置 GPIO 引脚和电平极性，提供开、关、闪烁功能。
    """

    def __init__(self, pin=4, on_value=1):
        """
        初始化闪光灯控制。

        参数：
            pin (int): GPIO 引脚编号，默认 4（ESP32-CAM 板载 LED）。
            on_value (int): 点亮电平值，1 表示高电平点亮，0 表示低电平点亮。
                             默认 1（高电平点亮），请根据实际硬件连接调整。
        """
        self.pin = Pin(pin, Pin.OUT)
        self.on_value = on_value
        self.off_value = 1 - on_value
        self.off()
        _debug_log("Flash initialized on pin {} (on_value={})".format(pin, on_value))

    def on(self):
        """打开闪光灯（输出点亮电平）。"""
        self.pin.value(self.on_value)
        _debug_log("Flash ON")

    def off(self):
        """关闭闪光灯（输出熄灭电平）。"""
        self.pin.value(self.off_value)
        _debug_log("Flash OFF")

    def blink(self, on_time=200, off_time=200):
        """
        闪烁一次（开灯 -> 等待 -> 关灯 -> 等待）。

        参数：
            on_time (int): 开灯持续时间（毫秒），默认 200ms。
            off_time (int): 关灯后等待时间（毫秒），默认 200ms。
        """
        _debug_log("Blinking: ON {}ms, OFF {}ms".format(on_time, off_time))
        self.on()
        time.sleep_ms(on_time)
        self.off()
        time.sleep_ms(off_time)

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- Flash 模块测试 ---")
    start = time.ticks_ms()

    # 测试创建单例
    f1 = get_flash()
    f2 = get_flash()
    print("单例验证: f1 is f2 =", f1 is f2)

    # 测试开/关
    print("闪烁测试...")
    f1.blink(100, 100)
    time.sleep_ms(200)
    f1.on()
    time.sleep_ms(300)
    f1.off()

    # 测试重置
    reset_flash()
    f3 = get_flash(pin=4, on_value=1)
    print("重置后创建新实例:", f3 is not f1)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))