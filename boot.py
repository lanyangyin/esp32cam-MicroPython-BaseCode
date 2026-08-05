# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import machine, uos
from machine import Pin

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