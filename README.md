# ESP32-CAM 智能拍照系统

基于 MicroPython 的 ESP32-CAM 多功能拍照与图像分析工具包。提供模块化的摄像头控制、智能闪光灯决策、快速连拍、亮度分析、视频录制基准测试等功能，适用于物联网、智能家居、安防监控等场景。

---

## 🚀 特性

- **模块化设计**：硬件抽象、决策引擎、工具函数、业务逻辑完全解耦，便于二次开发
- **智能闪光灯决策**：基于规则引擎或快速阈值，根据环境亮度自动控制闪光灯
- **自动分辨率降级**：当高分辨率初始化失败时，自动尝试较低分辨率
- **黑照检测**：基于 JPEG 大小判断无效照片，支持重试
- **亮度重试机制**：分析亮度时若信息异常（如全黑），自动重试直到稳定
- **快速连拍 / 视频录制**：多个录制器变体（按时间/帧数，时间戳/序号文件名），支持 10MHz/20MHz 时钟
- **帧率基准测试**：自动测试所有分辨率，输出帧率统计表
- **交互式决策调参**：通过串口终端辅助调整闪光灯规则阈值
- **完善的日志系统**：分级日志（DEBUG/INFO/WARNING/ERROR/CRITICAL），支持输出到终端或 SD 卡文件
- **支持图像格式**：JPEG 拍照，灰度/RAW/PGM/BMP/PPM 编码工具

---

## 🧱 硬件要求

- **主板**：ESP32-CAM 模块（ESP32 芯片 + 摄像头）
- **摄像头传感器**：OV2640 或 OV3660（固件需支持）
- **外部存储**：Micro SD 卡（建议 Class 10 以上SDHC）
- **电源**：5V/2A 稳压电源（电压不稳会导致 FB-OVF 错误）

---

## 📁 项目结构

```
/
├── app.py                      # 应用入口（智能拍照示例）
├── boot.py                     # 启动挂载 SD 卡、关闭闪光灯
├── main.py                     # 空（防止自动运行）
├── quick_photo_taking.py       # 独立快速拍照脚本（不依赖模块）
├── setup_default_configs.py    # 生成默认决策配置文件
│
├── config/                     # 配置管理包
│   ├── debug.py                # 日志分级、文件输出
│   ├── defaults.py             # 保守默认配置模板
│   ├── flash_config.py         # 闪光灯规则 CRUD
│   ├── retry_config.py         # 重拍规则 CRUD
│   └── __init__.py
│
├── camera_driver/              # 摄像头硬件驱动
│   ├── controller.py           # CameraController 类（初始化/捕获/释放）
│   ├── capture.py              # capture_image / capture_grayscale
│   ├── analysis.py             # 从摄像头捕获并分析亮度
│   ├── resolutions.py          # 分辨率映射表（常量->尺寸）
│   ├── singleton.py            # 单例管理
│   └── __init__.py
│
├── flash/                      # 闪光灯控制（单例）——根目录 flash.py
├── sd_card/                    # SD 卡管理（单例）——根目录 sd_card.py
├── wifi.py / ble.py            # WiFi / BLE 模块（可选）
│
├── decision/                   # 智能决策引擎
│   ├── engine.py               # 条件表达式评估器
│   ├── flash.py                # 正常闪光灯决策（规则引擎）
│   ├── quick_flash.py          # 快速闪光灯决策（阈值）
│   ├── retry.py                # 亮度重拍决策
│   ├── black_photo.py          # 黑照检测
│   ├── flash_decision_helper.py # 交互式调参工具
│   └── __init__.py
│
├── photo/                      # 拍照业务逻辑
│   ├── photo_capturer.py       # PhotoCapturer 类（完整功能）
│   ├── smart_photo_taker.py    # 智能拍照流程（供 app 调用）
│   ├── downgrade_capture.py    # 自动降级拍照
│   ├── manual_photo_taker.py   # 手动控制闪光灯拍照
│   ├── brightness_analyzer.py  # 灰度分析工具
│   ├── smart_capture_flow.py   # 智能拍照核心流程（被 capturer 调用）
│   ├── resource_manager.py     # 硬件资源清理/重置
│   └── __init__.py
│
├── video/                      # 快速连拍 / 录制
│   ├── recorder.py             # 通用录制器（带日志、闪光灯）
│   ├── recorder_fast.py        # 极速录制器（无日志，可保持常开）
│   ├── recorder_time.py        # 按时间录制（14秒GC，序号文件名）
│   ├── recorder_timestamp.py   # 按时间录制（时间戳文件名）
│   ├── recorder_frames.py      # 按帧数录制（50帧GC）
│   ├── benchmark.py            # 帧率基准测试（可选择录制器）
│   └── __init__.py
│
└── utils/                      # 纯工具函数（无硬件依赖）
    ├── brightness.py           # 亮度分析（avg, rms_contrast, center）
    ├── contrast.py             # RMS 对比度计算（标准差）
    ├── image_info.py           # JPEG/PNG 尺寸/格式提取
    ├── image_encoders.py       # BMP/PPM/PGM/RAW 编码
    ├── test_images.py          # 生成测试用灰度图
    ├── file_io.py              # 从 SD 卡加载图片
    ├── device_info.py          # 打印硬件信息
    └── __init__.py
```

---

## 🔧 安装与配置

### 1. 刷写 MicroPython 固件

- 下载 ESP32-CAM 专用的 MicroPython 固件（支持 camera 模块）
- 使用 esptool.py 刷写（示例）：
  ```
  esptool.py --chip esp32 --port COM3 erase_flash
  esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 firmware.bin
  ```

### 2. 上传项目文件

使用`mpremote`或`rshell`将整个项目目录上传到 ESP32 的根文件系统：

```
mpremote cp -r ./config /flash/
mpremote cp -r ./camera_driver /flash/
# ... 依次上传所有包和根文件
```

### 3. 生成默认配置文件

在 REPL 中执行一次（仅首次）：

```
import setup_default_configs
setup_default_configs.create_all()
```

这会在`/sd`下生成`flash_guide.json`、`retry_guide.json`、`quick_flash_guide.json`。

### 4. 电源检查

确保供电稳定（5V），否则可能导致摄像头初始化失败或 FB-OVF 错误。

---

## [WebREPL 连接](https://micropython.org/webrepl/)
WebREPL 是 MicroPython 官方提供的一项功能，让你能通过网络（WiFi）在浏览器中与 ESP32 进行交互，并获得一个 Python 命令行（REPL）-。它类似于一个通过网页访问的“无线串口”，非常方便。

### 🚀 如何启用和配置 WebREPL

WebREPL 默认是关闭的，需要手动启用并设置密码-。

1. **通过串口连接**：首先，用 USB 数据线将 ESP32-CAM 连接到电脑，并通过串口工具（如`mpremote`、Putty 或 Thonny）进入 MicroPython REPL。
2. **运行配置向导**：在 REPL 中执行以下命令，会启动一个配置向导-[-14](https://blog.csdn.net/skywalk8163/article/details/143856766)：
  ```
  import webrepl_setup
  ```
3. **根据提示操作**：按照向导的提示进行设置-[-14](https://blog.csdn.net/skywalk8163/article/details/143856766)：
    - 它会询问你是否要在开机时自动启动 WebREPL，输入`E`并回车以启用（Enable）。
    - 然后，系统会要求你设置一个**4 到 9 位**的密码（例如`123456`），并再次输入确认。
    - 最后，它会询问是否立即重启以使设置生效，输入`y`并回车。

### 🔌 如何连接 WebREPL

完成配置并重启后，就可以连接了。

#### 1. 准备网络环境

确保你的电脑和 ESP32-CAM 连接在**同一个局域网（WiFi）**下-[-14](https://blog.csdn.net/skywalk8163/article/details/143856766)。你需要先在 ESP32 上运行连接 WiFi 的代码，例如[-14](https://blog.csdn.net/skywalk8163/article/details/143856766):

```
import network
nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect("你的WiFi名称", "你的WiFi密码")
```

#### 2. 获取 ESP32 的 IP 地址

连接 WiFi 后，获取 ESP32 的 IP 地址-。在 REPL 中执行：

```
nic.ifconfig()
```

记下输出的第一个地址，例如`192.168.1.100`。

#### 3. 使用浏览器连接

- **官方 Web 客户端**：在电脑浏览器中打开官方 WebREPL 客户端：[https://micropython.org/webrepl/](https://micropython.org/webrepl/)。
- **输入地址和密码**：在页面中输入`ws://你的ESP32的IP地址:8266/`（例如`ws://192.168.1.100:8266/`），然后点击“Connect”。之后输入你之前设置的密码-。
  > **提示**：`8266`是 WebREPL 的默认端口-。

### 🛠 如何手动控制 WebREPL

如果不想让 WebREPL 开机自启，也可以随时手动启动或停止[-14](https://blog.csdn.net/skywalk8163/article/details/143856766)。

- **手动启动**：你也可以在启动时指定密码，覆盖配置文件中的设置-:
  ```
  import webrepl
  webrepl.start()
  ```
  ```
  webrepl.start(password="你的新密码")
  ```
- **手动停止**：该命令会关闭 WebREPL 服务并断开所有现有连接。
  ```
  import webrepl
  webrepl.stop()
  ```

## 📸 使用示例

### 最简单的智能拍照（app.py）

```
from photo import take_smart_photo
import camera

saved_path, w, h, brightness = take_smart_photo(
    analysis_framesize=camera.FRAME_QVGA,   # 分析亮度用分辨率
    photo_framesize=camera.FRAME_XGA,       # 最终照片分辨率
    retry_analysis_limit=6,                # 亮度重试次数
    retry_capture_limit=6,                 # 拍照重试次数
    decision_mode='normal'                 # 'normal' 或 'quick'
)
if saved_path:
    print(f"照片保存: {saved_path} ({w}x{h})")
```

### 快速录制 10 秒视频（帧序列）

```
from video import RecorderTime
import camera

recorder = RecorderTime(
    framesize=camera.FRAME_VGA,
    quality=10,
    xclk_freq=camera.XCLK_20MHz,
    save_dir="video_clip"
)
frames, elapsed = recorder.start(duration_sec=10)
print(f"{frames} 帧, {elapsed:.1f} 秒, {frames/elapsed:.1f} fps")
recorder.close()
```

### 帧率基准测试

```
from video import run_benchmark
import camera

# 使用快速录制器，10MHz 时钟，每个分辨率录 5 秒
run_benchmark(duration=5, recorder_type='fast', xclk_freq=camera.XCLK_10MHz)

# 使用按时间录制器，20MHz 时钟
run_benchmark(duration=5, recorder_type='time', xclk_freq=camera.XCLK_20MHz)
```

### 交互式调参（闪光灯决策）

```
from decision import flash_decision_helper

flash_decision_helper()   # 会捕获一帧灰度并显示决策，用户可修改规则条件
```

---

## ⚙️ 决策配置说明

### 正常闪光灯规则（flash_guide.json）

支持条件表达式（变量：`avg`,`rms`,`center`,`dynamic`）：

```
{
  "flash_conditions": [
    {
      "id": "very_dark_scene",
      "description": "场景极暗",
      "condition": "avg < 30",
      "action": "flash_on"
    },
    {
      "id": "backlit_scene",
      "description": "逆光场景",
      "condition": "rms > 40 and avg < 100",
      "action": "flash_on"
    }
  ],
  "default_action": {"flash": "off"},
  "camera_settings": { ... }
}
```

### 快速闪光灯决策（quick_flash_guide.json）

仅基于平均亮度阈值：

```
{
  "threshold": 30,
  "default_action": "off"
}
```

### 重拍决策（retry_guide.json）

当亮度信息异常时重新获取：

```
{
  "retry_conditions": [
    {
      "id": "invalid_brightness",
      "condition": "avg < 3 and dynamic < 2.5 and center < 3",
      "action": "retry_analysis"
    }
  ]
}
```

---

## 📊 日志系统

- 支持 5 个级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
- 可通过`set_log_level(LEVEL_DEBUG)`控制输出级别
- 可通过`set_log_to_file(True, "/sd/log.txt")`将日志写入 SD 卡
- 默认 INFO 级别输出到终端，便于调试

---

## 🤝 贡献与许可证

本项目采用**GNU General Public License v3.0**开源协议。

- 您可自由使用、修改、分发，但必须保留版权声明和许可声明。
- 任何衍生作品也必须在 GPLv3 下开源。

---

## 📖 参考文档

- [ESP32-CAM MicroPython 驱动](https://github.com/lemariva/micropython-camera-driver)

---

## ⚠️ 常见问题

| 问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| cam_hal: FB-OVF | 电压不足或分辨率过高 | 使用稳定 5V 电源，降低分辨率或 xclk 频率 |
| Camera Init Failed | 摄像头未连接或电源不足 | 检查排线，确保 5V/2A 供电 |
| 照片尺寸不对 | 驱动自动降级 | 日志会显示“设定”和“实际”尺寸，属正常行为 |
| SD 卡写入慢 | 卡速低或文件碎片多 | 使用 Class 10 卡，格式化 FAT32 |

---

## 🔗 作者

由 [[lanyangyin](https://github.com/lanyangyin)] 开发，基于社区 ESP32-CAM 项目改进。

**最后更新**: 2026-08-09