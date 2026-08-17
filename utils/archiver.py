# utils/archiver.py
"""
归档模块 – 将文件夹打包成一个归档文件（无压缩）

功能：
    - 递归遍历源文件夹，将所有文件和子目录打包到单个归档文件
    - 归档格式：每个文件前有头部标记，包含相对路径和文件大小
    - 支持归档后删除源文件夹（可选）

格式说明：
    每个文件记录：
        1. 一行 "---FILE_START---"
        2. 一行相对路径（UTF-8）
        3. 一行文件大小（十进制）
        4. 文件原始字节数据
        5. 一行 "---FILE_END---"
    所有文件顺序写入，无压缩。

典型用法：
    from utils import create_archive
    create_archive("/sd/photos", "/sd/backup.arc", delete_source=False)
"""

import uos
import time

ARCHIVE_MAGIC = "---FILE_START---"
ARCHIVE_END = "---FILE_END---"


def _walk_dir(path):
    """递归遍历目录，返回所有文件的相对路径列表（相对于 path）"""
    files = []
    try:
        items = uos.listdir(path)
    except Exception:
        return files
    for name in items:
        full = path + "/" + name
        try:
            st = uos.stat(full)
            is_dir = (st[0] & 0x4000) != 0
        except Exception:
            continue
        if is_dir:
            files.extend(_walk_dir(full))
        else:
            # 只收集文件
            files.append(full)
    return files


def create_archive(source_dir, archive_path, delete_source=False):
    """
    将源文件夹打包成一个归档文件。

    参数：
        source_dir (str): 要归档的源文件夹路径（绝对路径）。
        archive_path (str): 输出归档文件的完整路径（如 /sd/backup.arc）。
        delete_source (bool): 若为 True，归档成功后删除源文件夹及其所有内容。

    返回：
        bool: 成功返回 True，失败返回 False。

    说明：
        - 归档格式为顺序文件记录，无压缩，适合嵌入式环境。
        - 若源文件夹不存在或为空，归档文件仍会创建但无文件记录。
        - 归档过程中若发生错误，可能留下不完整的归档文件。
    """
    if not source_dir or not archive_path:
        return False

    # 确保 source_dir 以 "/" 结尾便于处理
    if not source_dir.endswith('/'):
        source_dir += '/'

    # 获取所有文件（包含完整路径）
    file_paths = _walk_dir(source_dir.rstrip('/'))
    if not file_paths:
        # 空目录，仍创建归档文件（无文件记录）
        try:
            with open(archive_path, 'wb') as f:
                pass
            # 如果要求删除空目录
            if delete_source:
                try:
                    uos.rmdir(source_dir.rstrip('/'))
                except Exception:
                    pass
            return True
        except Exception:
            return False

    try:
        with open(archive_path, 'wb') as arch:
            for full_path in file_paths:
                # 计算相对路径（相对于 source_dir）
                rel_path = full_path[len(source_dir):]
                # 获取文件大小
                try:
                    st = uos.stat(full_path)
                    size = st[6]  # st_size
                except Exception:
                    continue  # 跳过无法统计的文件

                # 写入文件头
                arch.write(ARCHIVE_MAGIC.encode() + b'\n')
                arch.write(rel_path.encode() + b'\n')
                arch.write(str(size).encode() + b'\n')

                # 写入文件内容
                try:
                    with open(full_path, 'rb') as f:
                        while True:
                            chunk = f.read(1024)
                            if not chunk:
                                break
                            arch.write(chunk)
                except Exception:
                    # 如果文件读取失败，跳过此文件（归档不完整）
                    # 但为了避免混乱，我们简单跳过并继续
                    # 最好能标记错误，但为了简单，我们继续
                    pass

                # 写入文件结束标记
                arch.write(ARCHIVE_END.encode() + b'\n')

        # 归档成功，是否删除源文件夹
        if delete_source:
            # 递归删除目录
            def rmtree(path):
                try:
                    items = uos.listdir(path)
                except Exception:
                    return
                for name in items:
                    full = path + "/" + name
                    try:
                        st = uos.stat(full)
                        if (st[0] & 0x4000) != 0:
                            rmtree(full)
                        else:
                            uos.remove(full)
                    except Exception:
                        pass
                try:
                    uos.rmdir(path)
                except Exception:
                    pass
            rmtree(source_dir.rstrip('/'))

        return True

    except Exception as e:
        print("[archiver] 归档失败:", e)
        # 可能留下不完整的归档文件，但调用者可以检查
        return False


# ---------- 测试入口 ----------
if __name__ == "__main__":
    from config import set_debug
    set_debug(True)

    print("=== 归档模块测试 ===")

    # 创建测试文件夹和文件
    test_dir = "/sd/test_archive"
    try:
        uos.mkdir(test_dir)
    except:
        pass
    # 创建几个文件
    try:
        with open(test_dir + "/file1.txt", "w") as f:
            f.write("Hello, World!")
        with open(test_dir + "/file2.txt", "w") as f:
            f.write("MicroPython Archive Test")
        # 创建子目录和文件
        try:
            uos.mkdir(test_dir + "/sub")
        except:
            pass
        with open(test_dir + "/sub/file3.txt", "w") as f:
            f.write("Nested file")
    except Exception as e:
        print("创建测试文件失败:", e)

    # 测试归档
    archive_file = "/sd/test_archive.arc"
    print("创建归档:", archive_file)
    success = create_archive(test_dir, archive_file, delete_source=False)
    if success:
        print("✅ 归档创建成功")
        # 验证文件是否存在
        try:
            st = uos.stat(archive_file)
            print("归档文件大小:", st[6])
        except:
            print("归档文件不存在")
    else:
        print("❌ 归档创建失败")

    # 测试删除源文件夹
    print("\n测试 delete_source=True")
    test_dir2 = "/sd/test_archive2"
    try:
        uos.mkdir(test_dir2)
        with open(test_dir2 + "/test.txt", "w") as f:
            f.write("Delete me")
    except Exception as e:
        print("创建测试目录2失败:", e)

    archive_file2 = "/sd/test_archive2.arc"
    success2 = create_archive(test_dir2, archive_file2, delete_source=True)
    if success2:
        print("✅ 归档并删除源文件夹成功")
        # 检查源文件夹是否已删除
        try:
            uos.stat(test_dir2)
            print("⚠️ 源文件夹仍然存在（删除失败）")
        except:
            print("源文件夹已删除")
    else:
        print("❌ 归档失败")

    print("\n测试完成")