# utils/file_io.py
"""
从文件系统加载图片数据
"""
import uos

def load_image_from_file(filepath):
    """
    从文件读取二进制数据（适用于 JPEG/PNG 等）。
    """
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except Exception as e:
        print("[file_io] Failed to load from {}: {}".format(filepath, e))
        return None


# ---------- 独立测试 ----------
if __name__ == "__main__":
    print("\n--- file_io 模块测试 ---")
    try:
        files = uos.listdir('/sd')
        jpgs = [f for f in files if f.lower().endswith('.jpg')]
        if jpgs:
            test_file = '/sd/' + jpgs[0]
            data = load_image_from_file(test_file)
            print(f"加载 {test_file} 成功，大小 {len(data)} 字节")
        else:
            print("未找到 /sd 下的 JPEG 文件")
    except Exception as e:
        print("测试失败:", e)