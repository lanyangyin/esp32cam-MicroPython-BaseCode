# flash.py
from machine import Pin
import time

class Flash:
    """ESP32-CAM 闪光灯控制（默认 GPIO 4，低电平点亮）"""
    def __init__(self, pin=4, on_value=0):
        self.pin = Pin(pin, Pin.OUT)
        self.on_value = on_value          # 点亮电平（0 或 1）
        self.off_value = 1 - on_value
        self.off()                       # 初始关闭

    def on(self):
        self.pin.value(self.on_value)

    def off(self):
        self.pin.value(self.off_value)

    def blink(self, on_time=200, off_time=200):
        """闪烁一次，用于测试"""
        self.on()
        time.sleep_ms(on_time)
        self.off()
        time.sleep_ms(off_time)