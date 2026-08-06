"""
device_info.py - 设备硬件信息报告模块

本模块用于获取和打印 ESP32-CAM 的硬件资源信息，包括：
    1. 芯片信息：平台、固件版本、CPU 频率
    2. 内存信息：已分配堆内存、可用堆内存
    3. PSRAM 信息：检测是否存在并分配测试
    4. Flash 信息：总大小
    5. 内部文件系统（/）总大小和可用空间
    6. SD 卡信息：总大小、已使用、可用空间（如果已挂载）

本模块可作为系统诊断工具，帮助开发者了解当前设备的资源状态。

依赖关系：
    - gc: 垃圾回收（获取内存信息）
    - esp: Flash 大小查询
    - esp32: ESP32 特有功能
    - os: 文件系统统计
    - machine: 系统信息
    - sys: 平台信息
    - config: 调试开关

典型用法：
    import device_info
    device_info.print_info()
"""
# device_info.py
import gc, esp, esp32, os, machine, sys
import time
from config import DEBUG

def _debug_log(msg):
    if DEBUG:
        print("[DeviceInfo] " + msg)

def get_sd_info(mount_point="/sd"):
    try:
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
        return {'mounted': False}

def print_info():
    print("\n" + "="*40)
    print("  设备硬件信息报告")
    print("="*40)
    print("\n[芯片信息]")
    print(f"平台: {sys.platform}")
    print(f"固件版本: {os.uname().release} ({os.uname().version})")
    print(f"CPU 频率: {machine.freq() // 1000000} MHz")
    print("\n[内存信息]")
    gc.collect()
    print(f"已分配堆内存: {gc.mem_alloc():,} 字节")
    print(f"可用堆内存:   {gc.mem_free():,} 字节")
    print(f"总堆内存:     {gc.mem_alloc() + gc.mem_free():,} 字节")
    print("\n[PSRAM 信息]")
    try:
        test_size = 2 * 1024 * 1024
        buf = bytearray(test_size)
        print(f"✅ PSRAM 可用 (至少分配了 {test_size // (1024*1024)} MB)")
        del buf
        gc.collect()
    except MemoryError:
        print("❌ PSRAM 可能不可用或容量不足")
    print("\n[Flash 信息]")
    try:
        flash_size_mb = esp.flash_size() // (1024 * 1024)
        print(f"Flash 总大小: {flash_size_mb} MB")
    except:
        print("Flash 大小: 无法获取")
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
    from config import set_debug
    set_debug(True)
    print("\n--- 设备硬件信息报告 ---")
    start = time.ticks_ms()
    print_info()
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("报告生成耗时 {} ms".format(elapsed))