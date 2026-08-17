# utils/unarchiver.py
"""
解压模块 – 从归档文件中提取文件到目标文件夹

功能：
    - 读取由 archiver.py 创建的归档文件
    - 提取所有文件到指定目录（自动创建目录结构）
    - 若目标目录不存在则自动创建

典型用法：
    from utils import extract_archive
    extract_archive("/sd/backup.arc", "/sd/restored")
"""

import uos

ARCHIVE_MAGIC = "---FILE_START---"
ARCHIVE_END = "---FILE_END---"


def _ensure_dir(path):
    """确保目录存在，逐级创建"""
    parts = path.split('/')
    current = ''
    for part in parts:
        if not part:
            continue
        current += '/' + part
        try:
            uos.mkdir(current)
        except OSError:
            pass  # 目录已存在


def extract_archive(archive_path, target_dir=None):
    """
    解压归档文件到目标目录。

    参数：
        archive_path (str): 归档文件的完整路径。
        target_dir (str): 目标目录路径（绝对路径），若为 None 则解压到当前目录（/sd）。

    返回：
        list: 成功解压的文件路径列表（相对或绝对路径取决于 target_dir），若失败返回空列表。

    说明：
        - 自动创建目标目录及其子目录。
        - 如果归档文件格式错误，会跳过错误记录并继续尝试。
        - 同名文件将被覆盖。
    """
    if target_dir is None:
        target_dir = "/sd"
    # 确保目标目录存在
    _ensure_dir(target_dir.rstrip('/'))

    extracted_files = []

    try:
        with open(archive_path, 'rb') as f:
            while True:
                # 读一行，查找起始标记
                line = f.readline()
                if not line:
                    break  # EOF
                line = line.decode().strip()
                if line == ARCHIVE_MAGIC:
                    # 读文件名
                    name_line = f.readline()
                    if not name_line:
                        break
                    rel_path = name_line.decode().strip()
                    # 读文件大小
                    size_line = f.readline()
                    if not size_line:
                        break
                    try:
                        size = int(size_line.decode().strip())
                    except ValueError:
                        break
                    # 读文件数据
                    data = f.read(size)
                    if len(data) != size:
                        # 数据不完整，跳出
                        break
                    # 读结束标记
                    end_line = f.readline()
                    if end_line:
                        end_line = end_line.decode().strip()
                        if end_line == ARCHIVE_END:
                            # 写入文件
                            target_full = target_dir.rstrip('/') + '/' + rel_path
                            # 确保父目录存在
                            parent = target_full.rsplit('/', 1)[0]
                            _ensure_dir(parent)
                            try:
                                with open(target_full, 'wb') as out:
                                    out.write(data)
                                extracted_files.append(target_full)
                                print("[unarchiver] 提取: {}".format(target_full))
                            except Exception as e:
                                print("[unarchiver] 写入文件失败:", e)
                        else:
                            # 结束标记不匹配，可能损坏，跳过此文件
                            print("[unarchiver] 结束标记不匹配，跳过文件:", rel_path)
                    else:
                        break  # EOF 异常
                else:
                    # 忽略其他行（可能残留）
                    continue
    except Exception as e:
        print("[unarchiver] 解压失败:", e)
        return []

    return extracted_files


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("=== 解压模块测试 ===")

    # 如果存在测试归档文件，则解压
    test_archive = "/sd/test_archive.arc"
    try:
        uos.stat(test_archive)
        print("找到测试归档文件，开始解压...")
        target = "/sd/extracted_test"
        files = extract_archive(test_archive, target)
        if files:
            print("✅ 解压成功，共 {} 个文件".format(len(files)))
            for f in files:
                print("  -", f)
        else:
            print("❌ 解压失败或没有文件")
    except Exception as e:
        print("测试归档文件不存在，跳过解压测试")
        print("请先运行 archiver.py 创建测试归档")

    print("\n测试完成")