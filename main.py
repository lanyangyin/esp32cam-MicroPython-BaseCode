# main.py
# 此文件留空，防止开机自动执行应用逻辑
# 若需自动运行 app.py，可在此写入:
import time
from indicator import get_indicator


print("开机暂停5秒 给足时间 ctrl+c 中断 ")
time.sleep(5)

# 获取单例（默认 GPIO 33，低电平点亮）
led = get_indicator()

# 开机闪烁一次
led.pulse(500)

# 在关键操作时闪烁
led.blink(2, 100, 100)

import web

web.start(port=80)  # 默认端口 80