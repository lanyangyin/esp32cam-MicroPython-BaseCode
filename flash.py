# flash.py
from machine import Pin
import time


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
        self.on_value = on_value  # 点亮电平（0 或 1）
        self.off_value = 1 - on_value  # 熄灭电平（与点亮相反）
        self.off()  # 初始关闭

    def on(self):
        """打开闪光灯（输出点亮电平）。"""
        self.pin.value(self.on_value)

    def off(self):
        """关闭闪光灯（输出熄灭电平）。"""
        self.pin.value(self.off_value)

    def blink(self, on_time=200, off_time=200):
        """
        闪烁一次（开灯 -> 等待 -> 关灯 -> 等待）。

        参数：
            on_time (int): 开灯持续时间（毫秒），默认 200ms。
            off_time (int): 关灯后等待时间（毫秒），默认 200ms。
        """
        self.on()
        time.sleep_ms(on_time)
        self.off()
        time.sleep_ms(off_time)