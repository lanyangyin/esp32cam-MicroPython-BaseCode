"""
boot.py - ESP32 启动初始化脚本

本文件在每次 ESP32 启动（包括从深度睡眠唤醒）时自动执行。
主要负责：
1. 关闭闪光灯（GPIO 4 输出低电平），确保启动时灯处于关闭状态
2. 挂载 SD 卡到 /sd，并列出根目录文件以验证挂载成功

依赖：
    - machine.Pin：GPIO 控制
    - machine.SDCard：SD 卡 SPI 接口
    - uos：文件系统操作

注意事项：
    - 本文件在 boot.py 阶段执行，此时 MicroPython 环境已就绪
    - 如果 SD 卡挂载失败，会打印错误信息但不影响后续启动
    - 本文件不涉及摄像头初始化，摄像头由各应用模块按需初始化

用法：
    无需手动调用，每次启动自动执行。
"""
# This file is executed on every boot (including wake-boot from deepsleep)
# import esp
# esp.osdebug(None)
# import webrepl
# webrepl.start(password="0000")
# # webrepl.stop()
import machine, uos
from machine import Pin
import network

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32-CAM-AP-{}".format(':'.join(['{:02x}'.format(b) for b in ap.config('mac')]).replace(':','').upper()[-4:]), password="00000000", authmode=network.AUTH_WPA_WPA2_PSK)
print("AP IP:", ap.ifconfig()[0])   # 通常为 192.168.4.1
# ap.active(False)

# 关闪光灯
led = Pin(4, Pin.OUT)
led.value(0)

# 挂载 SD 卡
try:
    sd = machine.SDCard()
    uos.mount(sd, "/sd")
    uos.listdir("/sd")
    print("SD mounted（sd挂载）")
except Exception as e:
    print("SD mount failed（挂载失败）:", e)