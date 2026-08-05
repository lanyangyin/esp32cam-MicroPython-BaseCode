# adjust_camera_settings.py
import camera
import time
from machine import Pin

# ========== 1. 关闭闪光灯 ==========
led = Pin(4, Pin.OUT)
led.value(0)   # 低电平关闭（根据你的实际极性调整）
time.sleep_ms(50)

# ========== 2. 初始化摄像头 ==========
print("Init camera...")
try:
    camera.init(0,
                format=camera.JPEG,
                fb_location=camera.PSRAM,
                framesize=camera.FRAME_XGA,   # 1024x768
                xclk_freq=camera.XCLK_10MHz   # 可选 10/20MHz，OV3660 建议 10MHz
                )
except Exception as e:
    print("Init failed:", e)
    raise

# ========== 3. 调整图像参数 ==========

# ---- 3.1 翻转和镜像 ----
camera.flip(1)      # 上下翻转（1 翻转，0 正常）
# camera.mirror(1)    # 左右镜像（1 镜像，0 正常）
# 如果同时 flip(1) 和 mirror(1)，等效于 180° 旋转。

# ---- 3.2 饱和度、亮度、对比度 ----
camera.saturation(0)    # -2 ~ 2，0 正常
camera.brightness(0)    # -2 ~ 2，0 正常
camera.contrast(0)      # -2 ~ 2，0 正常
# 若画面偏红，可尝试降低饱和度或调整白平衡。

# ---- 3.3 白平衡 ----
camera.whitebalance(camera.WB_CLOUDY)   # 自动模式
# 其他选项：WB_SUNNY, WB_CLOUDY, WB_OFFICE, WB_HOME
# 如果自动白平衡不准，可以手动选择对应光源。

# ---- 3.4 特殊效果 ----
camera.speffect(camera.EFFECT_NONE)   # 无特效
# 可选：EFFECT_NEG（负片）, EFFECT_BW（黑白）, EFFECT_RED/GREEN/BLUE, EFFECT_RETRO

# ---- 3.5 JPEG 质量 ----
camera.quality(10)    # 10 ~ 63，数值越小画质越好（文件越大）

# ========== 4. 开闪光灯并拍照 ==========
led.value(1)          # 开灯（根据你的实际电平极性）
time.sleep_ms(200)    # 等待曝光稳定

buf = camera.capture()
if not buf:
    print("Capture failed")
    camera.deinit()
    led.value(0)
    raise RuntimeError("No image")

led.value(0)          # 关灯

# ========== 5. 保存到 SD 卡 ==========
try:
    filename = "/sd/photo_calibrated_{}.jpg".format(time.time())
    with open(filename, "wb") as f:
        f.write(buf)
    print("Saved to", filename, "size:", len(buf))
except Exception as e:
    print("Save error:", e)

# ========== 6. 释放资源 ==========
camera.deinit()
print("Done")