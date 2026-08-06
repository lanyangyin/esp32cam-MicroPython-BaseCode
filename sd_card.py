# sd_card.py
import machine
import uos

class SDCardManager:
    """挂载 SD 卡并提供文件保存功能"""
    def __init__(self, mount_point="/sd", slot=2):
        self.mount_point = mount_point
        self.slot = slot
        self.mounted = False

    # sd_card.py 改进（增加已挂载检查）
    def mount(self):
        if self.mounted:
            return True
        # 检查是否已经挂载（可尝试 listdir 看是否报错）
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
            # pyrefly: ignore [missing-attribute]
            uos.mount(sd, self.mount_point)
            self.mounted = True
            print("SD card mounted")
            return True
        except Exception as e:
            print("SD mount failed:", e)
            return False

    def list_files(self):
        """列出根目录文件（调试用）"""
        if not self.mounted:
            self.mount()
        try:
            return uos.listdir(self.mount_point)
        except:
            return []

    def save_file(self, data, filename=None):
        """
        将数据保存到 SD 卡。
        若未提供文件名，则自动生成时间戳文件名。
        返回完整路径。
        """
        if not self.mounted:
            self.mount()
        if filename is None:
            import time
            filename = "photo_{}.jpg".format(time.time())
        # 确保以 /sd/ 开头
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