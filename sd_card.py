# sd_card.py
import machine
import uos


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

    def mount(self):
        """
        挂载 SD 卡。
        如果已挂载则直接返回 True；否则尝试列出挂载点，若失败则执行挂载操作。

        返回：
            bool: True 表示挂载成功或已挂载，False 表示挂载失败。
        """
        if self.mounted:
            return True
        # 检查是否已经挂载（通过尝试列出目录）
        try:
            uos.listdir(self.mount_point)
            self.mounted = True
            print("SD already mounted")
            return True
        except:
            pass
        # 否则尝试挂载
        try:
            sd = machine.SDCard(slot=self.slot)
            uos.mount(sd, self.mount_point)
            self.mounted = True
            print("SD card mounted")
            return True
        except Exception as e:
            print("SD mount failed:", e)
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
            return uos.listdir(self.mount_point)
        except:
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
            print("Saved to", filename)
            return filename
        except Exception as e:
            print("Save error:", e)
            return None