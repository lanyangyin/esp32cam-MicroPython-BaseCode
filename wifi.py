"""
wifi.py - WiFi 网络管理模块（单例模式）

提供 Station（连接外部 AP）和 Access Point（自建热点）两种模式，
支持切换、重连、获取 IP 等操作。

核心功能：
    - 单例管理：get_wifi() 获取唯一实例
    - 连接 STA：connect(ssid, password) 连接路由器
    - 开启 AP：start_ap(ssid, password) 创建热点
    - 状态查询：is_connected(), is_ap_active(), ip()
    - 自动重连：reconnect() 尝试重新连接

依赖：
    - network 模块（MicroPython 内置）
    - config.DEBUG 控制日志
"""
import time
import network
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="WiFi")


# ---------- 单例管理 ----------
_wifi_instance = None

def get_wifi():
    """获取 WiFi 单例对象"""
    global _wifi_instance
    if _wifi_instance is None:
        _wifi_instance = WiFiManager()
    return _wifi_instance

def reset_wifi():
    """重置单例（关闭并释放网络接口）"""
    global _wifi_instance
    if _wifi_instance is not None:
        _wifi_instance.deinit()
        _wifi_instance = None

# ---------- WiFiManager 类 ----------
class WiFiManager:
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.sta_active = False
        self.ap_active = False
        _debug_log("WiFiManager created")

    def deinit(self):
        """关闭所有网络接口"""
        if self.sta_active:
            self.sta.active(False)
            self.sta_active = False
        if self.ap_active:
            self.ap.active(False)
            self.ap_active = False
        _debug_log("WiFi deinitialized")

    # ---------- Station 模式 ----------
    def connect(self, ssid, password, timeout=15):
        """
        连接 WiFi 路由器（STA 模式）
        参数：
            ssid (str): 路由器 SSID
            password (str): 密码
            timeout (int): 超时秒数
        返回：
            bool: 连接成功返回 True，否则 False
        """
        if self.sta_active:
            if self.sta.isconnected():
                _debug_log("Already connected to {}".format(self.sta.config('essid')))
                return True
            self.sta.disconnect()
        self.sta.active(True)
        self.sta_active = True
        self.sta.connect(ssid, password)
        _debug_log("Connecting to {} ...".format(ssid))

        start = time.time()
        while not self.sta.isconnected():
            if time.time() - start > timeout:
                _debug_log("Connection timeout")
                return False
            time.sleep_ms(200)
        _debug_log("Connected, IP: {}".format(self.sta.ifconfig()[0]))
        return True

    def disconnect(self):
        """断开 STA 连接"""
        if self.sta_active:
            self.sta.disconnect()
            self.sta.active(False)
            self.sta_active = False
            _debug_log("STA disconnected")

    def is_connected(self):
        """检查 STA 是否已连接"""
        return self.sta_active and self.sta.isconnected()

    def get_sta_ip(self):
        """获取 STA IP 地址"""
        if self.is_connected():
            return self.sta.ifconfig()[0]
        return None

    # ---------- Access Point 模式 ----------
    def start_ap(self, ssid="ESP32-CAM", password="12345678", authmode=network.AUTH_WPA_WPA2_PSK, timeout=10):
        """
        开启 AP 热点模式
        参数：
            ssid (str): 热点名称
            password (str): 密码（至少 8 位）
            authmode: 加密方式，默认 WPA2
            timeout (int): 等待 AP 启动超时（秒）
        返回：
            bool: 成功返回 True
        """
        if self.ap_active:
            _debug_log("AP already active")
            return True
        self.ap.active(True)
        self.ap.config(essid=ssid, password=password, authmode=authmode)
        self.ap_active = True
        _debug_log("AP started: {} IP: {}".format(ssid, self.ap.ifconfig()[0]))
        return True

    def stop_ap(self):
        """关闭 AP"""
        if self.ap_active:
            self.ap.active(False)
            self.ap_active = False
            _debug_log("AP stopped")

    def is_ap_active(self):
        return self.ap_active

    def get_ap_ip(self):
        """获取 AP IP 地址（通常为 192.168.4.1）"""
        if self.ap_active:
            return self.ap.ifconfig()[0]
        return None

    # ---------- 通用查询 ----------
    def get_ip(self):
        """返回当前有效的 IP（优先 STA 的 IP）"""
        if self.is_connected():
            return self.get_sta_ip()
        elif self.is_ap_active():
            return self.get_ap_ip()
        return None

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    print("\n--- WiFi 模块测试 ---")
    wifi = get_wifi()

    # 测试 STA 连接（请替换为实际凭据）
    print("尝试连接路由器...")
    ok = wifi.connect("YourSSID", "YourPassword")
    if ok:
        print("STA IP:", wifi.get_sta_ip())
    else:
        print("STA 连接失败")

    # 测试 AP 模式
    print("\n启动 AP 热点...")
    wifi.start_ap(ssid="ESP32_TEST", password="12345678")
    print("AP IP:", wifi.get_ap_ip())
    print("当前有效 IP:", wifi.get_ip())

    # 清理
    wifi.deinit()
    reset_wifi()
    print("测试完成")