# sd_card.py
import machine
import uos
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[SD] " + msg)

# ---------- 单例管理 ----------
_sd_instance = None

def get_sd_card(mount_point="/sd", slot=2):
    """
    获取 SD 卡管理单例对象。
    第一次调用时创建并挂载，后续返回同一实例。
    若挂载失败，先尝试卸载再重试。

    参数：
        mount_point (str): 挂载点，默认 "/sd"。
        slot (int): SPI 槽位，默认 2。

    返回：
        SDCardManager: 单例实例。
    """
    global _sd_instance
    if _sd_instance is not None:
        _debug_log("Return existing SD instance")
        return _sd_instance

    _debug_log("Creating SD card manager...")
    try:
        _sd_instance = SDCardManager(mount_point, slot)
        _sd_instance.mount()
        _debug_log("SD card mounted successfully")
        return _sd_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        if _sd_instance is not None:
            try:
                uos.umount(_sd_instance.mount_point)
            except:
                pass
            _sd_instance = None
        # 重试
        try:
            _sd_instance = SDCardManager(mount_point, slot)
            _sd_instance.mount()
            _debug_log("SD card mounted on retry")
            return _sd_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise

def reset_sd_card():
    """强制释放并重置 SD 卡单例。"""
    global _sd_instance
    if _sd_instance is not None:
        _debug_log("Resetting SD singleton")
        try:
            uos.umount(_sd_instance.mount_point)
        except:
            pass
        _sd_instance = None

# ---------- SDCardManager 类 ----------
class SDCardManager:
    """
    SD 卡管理类。
    提供挂载、文件列表、文件保存等功能，支持自动检测是否已挂载。
    """

    def __init__(self, mount_point="/sd", slot=2):
        """
        初始化 SD 卡管理器。

        参数：
            mount_point (str): 挂载点路径，默认为 "/sd"。
            slot (int): SD 卡 SPI 槽位，通常为 2（ESP32-CAM 默认）。
        """
        self.mount_point = mount_point
        self.slot = slot
        self.mounted = False
        _debug_log("SDCardManager created (mount_point={}, slot={})".format(mount_point, slot))

    def mount(self):
        """
        挂载 SD 卡。
        如果已挂载则直接返回 True；否则尝试列出挂载点，若失败则执行挂载操作。

        返回：
            bool: True 表示挂载成功或已挂载，False 表示挂载失败。
        """
        if self.mounted:
            _debug_log("Already mounted")
            return True
        # 检查是否已经挂载（通过尝试列出目录）
        try:
            uos.listdir(self.mount_point)
            self.mounted = True
            _debug_log("SD already mounted (detected by listdir)")
            return True
        except:
            pass
        # 否则尝试挂载
        try:
            sd = machine.SDCard(slot=self.slot)
            uos.mount(sd, self.mount_point)
            self.mounted = True
            _debug_log("SD card mounted (new)")
            return True
        except Exception as e:
            _debug_log("Mount failed: {}".format(e))
            return False

    def list_files(self):
        """
        列出挂载点根目录下的所有文件。

        返回：
            list: 文件名列表，若未挂载或失败则返回空列表。
        """
        if not self.mounted:
            self.mount()
        try:
            files = uos.listdir(self.mount_point)
            _debug_log("Listed {} files".format(len(files)))
            return files
        except Exception as e:
            _debug_log("List files error: {}".format(e))
            return []

    def save_file(self, data, filename=None):
        """
        将数据保存到 SD 卡。

        参数：
            data (bytes): 要保存的二进制数据。
            filename (str): 文件名（可选），若为 None 则自动生成 `photo_时间戳.jpg`。
                             若文件名不含路径，则自动添加挂载点前缀。

        返回：
            str: 保存后的完整文件路径；若保存失败则返回 None。
        """
        if not self.mounted:
            self.mount()
        if filename is None:
            import time
            filename = "photo_{}.jpg".format(time.time())
        # 确保以挂载点开头
        if not filename.startswith(self.mount_point):
            filename = self.mount_point + "/" + filename.lstrip("/")
        try:
            with open(filename, "wb") as f:
                f.write(data)
            _debug_log("Saved file: {}".format(filename))
            return filename
        except Exception as e:
            _debug_log("Save error: {}".format(e))
            return None

# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    import time
    print("\n--- SD 卡模块测试 ---")
    start = time.ticks_ms()

    # 测试单例
    s1 = get_sd_card()
    s2 = get_sd_card()
    print("单例验证: s1 is s2 =", s1 is s2)

    # 列出文件
    files = s1.list_files()
    print("文件数:", len(files))

    # 测试保存一个小的数据文件（不实际写入大图片）
    test_data = b"Hello SD Card test"
    saved = s1.save_file(test_data, "test.txt")
    if saved:
        print("测试文件保存成功:", saved)
        # 删除测试文件
        try:
            uos.remove(saved)
            print("测试文件已删除")
        except:
            pass
    else:
        print("保存测试文件失败")

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("测试完成，耗时 {} ms".format(elapsed))