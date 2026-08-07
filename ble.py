"""
ble.py - 蓝牙低功耗（BLE）模块（单例模式）

提供简单的 BLE 外设（Peripheral）功能：
    - 广播设备名称
    - 可读写的自定义特性（Characteristic）
    - 接收数据回调

可用于手机 App 连接、发送拍照指令或接收状态。

依赖：
    - bluetooth 模块（MicroPython 内置）
    - ubluetooth 简化库（可选，此处使用原生）
    - config.DEBUG 控制日志
"""
import time
import bluetooth
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[BLE] " + msg)

# ---------- 单例管理 ----------
_ble_instance = None

def get_ble(device_name="ESP32-CAM"):
    """获取 BLE 单例对象"""
    global _ble_instance
    if _ble_instance is None:
        _ble_instance = BLESimplePeripheral(device_name)
    return _ble_instance

def reset_ble():
    """重置 BLE（停用蓝牙）"""
    global _ble_instance
    if _ble_instance is not None:
        _ble_instance.deinit()
        _ble_instance = None

# ---------- BLE 简单外设类 ----------
class BLESimplePeripheral:
    def __init__(self, name="ESP32-CAM"):
        self.name = name
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.config(gap_name=name)
        self.connected = False
        self.rx_data = b""
        self.callback = None

        # 注册事件回调
        self.ble.irq(self._irq)

        # 创建服务（自定义服务 UUID 可以是任意 16-bit/128-bit）
        self.service_uuid = bluetooth.UUID(0x180F)  # 电池服务示例，实际可自定义
        self.char_uuid = bluetooth.UUID(0x2A19)     # 电池电量，但此处我们使用读写特性
        # 推荐使用自定义 UUID（128-bit）避免冲突，这里简化用已知 UUID
        # 更严谨的做法：生成自定义 UUID
        self._create_services()

        # 开始广播
        self.advertise()

        _debug_log("BLE initialized, name: {}".format(name))

    def _irq(self, event, data):
        """BLE 事件处理"""
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            self.connected = True
            _debug_log("Central connected")
            if self.callback:
                self.callback("connected")

        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            self.connected = False
            _debug_log("Central disconnected")
            # 重新广播以便再次连接
            self.advertise()
            if self.callback:
                self.callback("disconnected")

        elif event == 3:  # _IRQ_GATTS_WRITE
            conn_handle, attr_handle = data
            # 读取写入的数据
            value = self.ble.gatts_read(attr_handle)
            self.rx_data = value
            _debug_log("Received: {}".format(value))
            if self.callback:
                self.callback("data", value)

    def _create_services(self):
        """创建服务和特征"""
        # 这里使用只读和读写特性（根据实际需求）
        # 我们定义两个特性：一个只读（设备名），一个可读写（指令通道）
        self.service = bluetooth.UUID(0x180F)   # 服务 UUID
        self.char_read = bluetooth.UUID(0x2A19) # 用于读取（电池电量）
        self.char_write = bluetooth.UUID(0x2A1C) # 用于写入（自定义）
        # 实际应用中建议使用自定义 128-bit UUID
        # 这里简化演示

        # 创建服务表
        self.ble.gatts_register_services([
            (self.service, [
                (self.char_read, bluetooth.FLAG_READ),
                (self.char_write, bluetooth.FLAG_WRITE | bluetooth.FLAG_READ),
            ])
        ])

        # 初始化特性值
        self.ble.gatts_write(self.char_read, b"ESP32-CAM")
        self.ble.gatts_write(self.char_write, b"")

    def advertise(self, interval_us=500000):
        """开始广播"""
        # 构造广播数据：包含设备名
        # MicroPython 的 bluetooth 提供 advertise 方法
        self.ble.gap_advertise(interval_us, adv_data=self.ble.adv_data(
            local_name=self.name,
            services=[self.service_uuid]
        ))
        _debug_log("Advertising")

    def deinit(self):
        """停用蓝牙"""
        self.ble.active(False)
        _debug_log("BLE deinitialized")

    def is_connected(self):
        return self.connected

    def send(self, data):
        """向连接的中央设备发送数据"""
        if self.connected:
            # 使用通知或指示，这里以通知为例
            # 需要获取对应的句柄，简化：使用 gatts_notify
            # 实际需获取特征句柄
            try:
                self.ble.gatts_notify(0, self.char_write, data)
                _debug_log("Sent: {}".format(data))
                return True
            except Exception as e:
                _debug_log("Send error: {}".format(e))
                return False
        return False

    def on_event(self, callback):
        """
        设置事件回调函数
        callback 接受 (event, *args) 参数：
            - event == "connected" 或 "disconnected"
            - event == "data" 时 args 包含接收的数据
        """
        self.callback = callback

    def get_rx_data(self):
        """获取接收到的数据（非阻塞，返回 bytes）"""
        data = self.rx_data
        self.rx_data = b""
        return data

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- BLE 模块测试 ---")
    ble = get_ble("ESP32_CAM_TEST")

    def on_event(event, *args):
        if event == "connected":
            print("[BLE] 中央设备已连接")
        elif event == "disconnected":
            print("[BLE] 中央设备已断开")
        elif event == "data":
            print("[BLE] 收到数据:", args[0])

    ble.on_event(on_event)

    print("BLE 正在广播，请使用手机 App 或 nRF Connect 连接")
    print("连接后可写入数据，设备会打印接收内容")
    print("按 Ctrl+C 退出...")

    try:
        while True:
            time.sleep_ms(500)
            data = ble.get_rx_data()
            if data:
                print("处理数据:", data)
                # 可以在这里执行拍照等操作
                # 例如：如果收到 b"photo" 则拍照
    except KeyboardInterrupt:
        print("\n退出测试")
        ble.deinit()
        reset_ble()