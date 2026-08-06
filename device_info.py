# device_info.py
import gc, esp, esp32, os, machine, sys

def get_sd_info(mount_point="/sd"):
    """
    检测 SD 卡挂载点信息。
    返回字典: {'total_mb': float, 'free_mb': float, 'used_mb': float, 'mounted': bool}
    """
    try:
        # 尝试列出目录检测是否挂载
        os.listdir(mount_point)
        vfs = os.statvfs(mount_point)
        block_size = vfs[0]
        total_blocks = vfs[2]
        free_blocks = vfs[3]
        total_mb = (block_size * total_blocks) / (1024 * 1024)
        free_mb = (block_size * free_blocks) / (1024 * 1024)
        used_mb = total_mb - free_mb
        return {
            'mounted': True,
            'total_mb': total_mb,
            'free_mb': free_mb,
            'used_mb': used_mb,
        }
    except OSError:
        # 挂载点不存在或未挂载
        return {'mounted': False}

def print_info():
    print("\n" + "="*40)
    print("  设备硬件信息报告")
    print("="*40)

    # --- 芯片信息 ---
    print("\n[芯片信息]")
    print(f"平台: {sys.platform}")
    print(f"固件版本: {os.uname().release} ({os.uname().version})")
    print(f"CPU 频率: {machine.freq() // 1000000} MHz")

    # --- 内存信息 ---
    print("\n[内存信息]")
    gc.collect()
    print(f"已分配堆内存: {gc.mem_alloc():,} 字节")
    print(f"可用堆内存:   {gc.mem_free():,} 字节")
    print(f"总堆内存:     {gc.mem_alloc() + gc.mem_free():,} 字节")

    # --- PSRAM 信息 ---
    print("\n[PSRAM 信息]")
    try:
        # 尝试分配一个大内存块来测试 PSRAM
        test_size = 2 * 1024 * 1024  # 2 MB
        buf = bytearray(test_size)
        print(f"✅ PSRAM 可用 (至少分配了 {test_size // (1024*1024)} MB)")
        del buf
        gc.collect()
    except MemoryError:
        print("❌ PSRAM 可能不可用或容量不足")

    # --- Flash 信息 ---
    print("\n[Flash 信息]")
    try:
        flash_size_mb = esp.flash_size() // (1024 * 1024)
        print(f"Flash 总大小: {flash_size_mb} MB")
    except:
        print("Flash 大小: 无法获取")

    # --- 内部文件系统（/）信息 ---
    print("\n[内部文件系统（/）]")
    try:
        vfs = os.statvfs('/')
        block_size = vfs[0]
        total_blocks = vfs[2]
        free_blocks = vfs[3]
        total_mb = (block_size * total_blocks) // (1024 * 1024)
        free_mb = (block_size * free_blocks) // (1024 * 1024)
        print(f"总大小:   {total_mb} MB")
        print(f"可用空间: {free_mb} MB")
    except:
        print("无法获取")

    # --- SD 卡信息（/sd） ---
    print("\n[SD 卡（/sd）]")
    sd_info = get_sd_info()
    if sd_info['mounted']:
        print(f"总大小:   {sd_info['total_mb']:.1f} MB")
        print(f"已使用:   {sd_info['used_mb']:.1f} MB")
        print(f"可用空间: {sd_info['free_mb']:.1f} MB")
    else:
        print("❌ SD 卡未挂载或不存在")

    print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    print_info()