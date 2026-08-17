# web/app.py
"""
使用 EasyWeb 框架的 Web 控制服务
支持模式选择：拍照 / 录制（视频预留）
"""

import sys
import time
import camera
import uos
import json
import network
import ujson
import easyweb

from advanced_photo import take_advanced_photo, burst_capture
from easyweb import EasyWeb, make_response
from photo import take_smart_photo, gray_quick_capture, gray_analyzer_capture
from video import RecorderTimestamp
from sd_card import get_sd_card
from config import set_debug, CAMERA_MODEL
from config.camera_model import get_config_path
from utils import create_archive
from utils import extract_archive as extract_archive_util

set_debug(True)

app = EasyWeb()

# ---------- 模式配置文件 ----------
MODE_FILE = "/web_mode.txt"

def _read_mode():
    try:
        with open(MODE_FILE, "r") as f:
            mode = f.read().strip()
            if mode in ("拍照", "录制", "视频"):
                return mode
            return None
    except:
        return None

def _write_mode(mode):
    try:
        with open(MODE_FILE, "w") as f:
            f.write(mode)
        return True
    except:
        return False

def _clear_mode():
    try:
        with open(MODE_FILE, "w") as f:
            f.write("")
        return True
    except:
        return False

def _get_resolutions():
    res = []
    for name in dir(camera):
        if name.startswith("FRAME_"):
            val = getattr(camera, name)
            w, h = 0, 0
            try:
                from camera_driver.resolutions import get_resolution
                w, h = get_resolution(val) or (0, 0)
            except:
                pass
            res.append({
                "name": name,
                "value": val,
                "width": w,
                "height": h
            })
    return res

def _render_html(template_name, **kwargs):
    """读取 HTML 模板并用 kwargs 替换占位符"""
    path = "/web/static/" + template_name
    try:
        with open(path, "r") as f:
            html = f.read()
        for key, value in kwargs.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            html = html.replace("{" + key + "}", str(value))
        return html
    except Exception as e:
        print("[Web] 读取模板失败:", e)
        return "<h1>Error loading page</h1><p>{}</p>".format(e)

# ---------- Wi-Fi 配置 ----------
WIFI_CONFIG_FILE = "/sd/wifi_config.json"
_current_ip = "0.0.0.0"

def _load_wifi_config():
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            config = ujson.load(f)
            return config.get("ssid", ""), config.get("password", "")
    except:
        return "", ""

def _save_wifi_config(ssid, password):
    try:
        config = {"ssid": ssid, "password": password}
        with open(WIFI_CONFIG_FILE, "w") as f:
            ujson.dump(config, f)
        return True
    except Exception as e:
        print("[Web] 保存 Wi-Fi 配置失败:", e)
        return False

def _connect_wifi(ssid, password):
    global _current_ip
    if not ssid:
        return False
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        if wlan.config('essid') == ssid:
            _current_ip = wlan.ifconfig()[0]
            return True
        else:
            wlan.disconnect()
    wlan.connect(ssid, password)
    timeout = 10
    while timeout > 0:
        if wlan.isconnected():
            _current_ip = wlan.ifconfig()[0]
            return True
        time.sleep(1)
        timeout -= 1
    return False

# ---------- 路由 ----------
@app.route("/")
def index(request):
    print("[Web] 请求: /")
    mode = _read_mode()
    if mode is None:
        print("[Web] 未选择模式，显示模式选择页")
        return make_response(_render_html("mode_selector.html"), 200)
    elif mode == "拍照":
        print("[Web] 当前模式: 拍照")
        resolutions = _get_resolutions()
        return make_response(_render_html("photo.html", resolutions=resolutions), 200)
    elif mode == "录制":
        print("[Web] 当前模式: 录制")
        resolutions = _get_resolutions()
        return make_response(_render_html("video.html", resolutions=resolutions), 200)
    elif mode == "视频":
        print("[Web] 当前模式: 视频 (未实现)")
        return make_response("<h1>视频模式即将上线</h1><p><a href='/set_mode?mode=拍照'>切换到拍照</a> | <a href='/set_mode?mode=录制'>切换到录制</a></p>", 200)
    else:
        _clear_mode()
        return make_response("Invalid mode, please reselect.", 302, {"Location": "/"})

@app.route("/set_mode", methods=["POST"])
def set_mode(request):
    mode = request.form.get("mode") if request.form else None
    print("[Web] /set_mode 收到 mode: {}".format(mode))
    if mode in ("拍照", "录制", "视频"):
        _write_mode(mode)
        print("[Web] 模式已设置为: {}".format(mode))
        return make_response({"success": True, "mode": mode}, 200)
    else:
        return make_response({"success": False, "error": "Invalid mode"}, 400)

# ---------- API：配置保存/加载 ----------
CONFIG_FILE = "/sd/camera_config.json"

@app.route("/api/save_config", methods=["POST"])
def save_config(request):
    try:
        config = request.json
        if not config:
            return make_response({"success": False, "error": "No config data"}, 400)
        print("[Web] 保存配置内容:", config)  # 添加这行
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("[Web] 配置已保存至 {}".format(CONFIG_FILE))
        return make_response({"success": True}, 200)
    except Exception as e:
        print("[Web] 保存配置失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

@app.route("/api/load_config", methods=["GET"])
def load_config(request):
    try:
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            print("[Web] 配置已加载")
            return make_response(config, 200)
        except OSError:
            default_config = {
                "flash_mode": "auto",
                "resolution": 1024,
                "whitebalance": 2,
                "mirror": 0,
                "flip": 1,
                "xclk_freq": 10000000,
                "saturation": 0,
                "brightness": 0,
                "contrast": 0,
                "quality": 10,
                "save_file": True,
                "filename_prefix": "photo",
                "save_path": "/sd",
                "black_retry": 3,
                "analysis_retry": 3,
                "analysis_resolution": 320,
                "burst_count": 5,
                "burst_flash": False,
                "burst_prefix": "burst",
                # 录制参数
                "video_framesize": 640,   # FRAME_VGA
                "video_quality": 10,
                "video_duration": 5,
                "video_save_dir": "video_web",
                "video_xclk_freq": 10000000,
            }
            print("[Web] 配置不存在，返回默认")
            return make_response(default_config, 200)
    except Exception as e:
        print("[Web] 加载配置失败:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- API：系统状态 ----------
@app.route("/api/status")
def status(request):
    print("[Web] 请求: /api/status")
    try:
        sd = get_sd_card()
        resolutions = _get_resolutions()
        wlan = network.WLAN(network.STA_IF)
        ip = wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"
        status_data = {
            "model": CAMERA_MODEL,
            "sd_mounted": sd.mounted if sd else False,
            "timestamp": time.time(),
            "resolutions": resolutions,
            "ip": ip,
        }
        return make_response(status_data, 200)
    except Exception as e:
        print("[Web] /api/status 错误:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- API：拍照 ----------
@app.route("/api/capture", methods=["POST"])
def capture(request):
    print("[Web] 请求: /api/capture")
    try:
        params = request.json if request.json else {}
        flash_mode = params.get("flash_mode", "auto")
        resolution = params.get("resolution", camera.FRAME_XGA)
        whitebalance = params.get("whitebalance", camera.WB_CLOUDY)
        mirror = params.get("mirror", 0)
        flip = params.get("flip", 1)
        xclk_freq = params.get("xclk_freq", camera.XCLK_10MHz)
        saturation = params.get("saturation", 0)
        brightness = params.get("brightness", 0)
        contrast = params.get("contrast", 0)
        quality = params.get("quality", 10)
        save_file = params.get("save_file", True)
        filename_prefix = params.get("filename_prefix", "photo")
        save_path = params.get("save_path", "/sd")
        black_retry = params.get("black_retry", 3)
        analysis_retry = params.get("analysis_retry", 3)
        analysis_resolution = params.get("analysis_resolution", camera.FRAME_QVGA)

        result = take_advanced_photo(
            flash_mode=flash_mode,
            resolution=resolution,
            whitebalance=whitebalance,
            mirror=mirror,
            flip=flip,
            xclk_freq=xclk_freq,
            saturation=saturation,
            brightness=brightness,
            contrast=contrast,
            quality=quality,
            save_file=save_file,
            filename_prefix=filename_prefix,
            save_path=save_path,
            black_retry=black_retry,
            analysis_retry=analysis_retry,
            analysis_resolution=analysis_resolution,
        )

        if result is None:
            return make_response({"success": False, "error": "Capture failed"}, 200)

        response = {
            "success": True,
            "path": result.get('path'),
            "width": result.get('width', 0),
            "height": result.get('height', 0),
            "brightness": result.get('brightness', 0),
        }
        return make_response(response, 200)
    except Exception as e:
        print("[Web] /api/capture 异常:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：连拍 ----------
@app.route("/api/burst", methods=["POST"])
def burst(request):
    print("[Web] 请求: /api/burst")
    try:
        params = request.json if request.json else {}
        resolution = params.get("resolution", camera.FRAME_XGA)
        whitebalance = params.get("whitebalance", camera.WB_CLOUDY)
        mirror = params.get("mirror", 0)
        flip = params.get("flip", 1)
        burst_count = params.get("burst_count", 5)
        xclk_freq = params.get("xclk_freq", camera.XCLK_10MHz)
        saturation = params.get("saturation", 0)
        brightness = params.get("brightness", 0)
        contrast = params.get("contrast", 0)
        quality = params.get("quality", 10)
        flash_on = params.get("flash_on", False)
        filename_prefix = params.get("filename_prefix", "burst")
        save_path = params.get("save_path", "/sd")
        elapsed = burst_capture(
            resolution=resolution,
            whitebalance=whitebalance,
            mirror=mirror,
            flip=flip,
            burst_count=burst_count,
            xclk_freq=xclk_freq,
            saturation=saturation,
            brightness=brightness,
            contrast=contrast,
            quality=quality,
            flash_on=flash_on,
            filename_prefix=filename_prefix,
            save_path=save_path,
        )
        if elapsed < 0:
            return make_response({"success": False, "error": "Burst capture failed"}, 200)
        else:
            return make_response({"success": True, "elapsed": elapsed, "frames": burst_count}, 200)
    except Exception as e:
        print("[Web] /api/burst 异常:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：录像 ----------
@app.route("/api/video", methods=["POST"])
def video(request):
    print("[Web] 请求: /api/video")
    try:
        params = request.json if request.json else {}
        framesize = params.get("framesize", camera.FRAME_VGA)
        quality = params.get("quality", 10)
        duration = params.get("duration", 5)
        xclk_freq = params.get("xclk_freq", camera.XCLK_10MHz)
        save_dir = params.get("save_dir", "video_web")
        print("[Web] 参数: framesize={}, duration={}s, xclk={}, save_dir={}".format(framesize, duration, xclk_freq, save_dir))
        recorder = RecorderTimestamp(
            framesize=framesize,
            quality=quality,
            xclk_freq=xclk_freq,
            save_dir=save_dir
        )
        frames, elapsed = recorder.start(duration_sec=duration)
        recorder.close()
        result = {
            "success": True,
            "frames": frames,
            "elapsed": elapsed,
            "fps": frames / elapsed if elapsed > 0 else 0
        }
        print("[Web] 录像完成: {}帧, {:.2f}s".format(frames, elapsed))
        return make_response(result, 200)
    except Exception as e:
        print("[Web] /api/video 异常:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- 文件与目录操作 ----------
ALLOWED_EXTS = ('.jpg', '.jpeg', '.ppm', '.bmp', '.raw', '.arc', '.tar', '.gz', '.zip')

def _list_directory(path):
    """
    返回目录下的条目，文件夹总是显示，文件只显示扩展名在 ALLOWED_EXTS 中的。
    """
    try:
        items = uos.listdir(path)
    except Exception:
        return []
    entries = []
    for name in items:
        full_path = path + '/' + name if path != '/' else '/' + name
        try:
            st = uos.stat(full_path)
            is_dir = (st[0] & 0x4000) != 0
        except Exception:
            continue
        if is_dir:
            if name == "System Volume Information":
                continue
            entries.append({
                "name": name,
                "is_dir": True,
                "path": full_path
            })
        else:
            # 检查扩展名
            lower_name = name.lower()
            if lower_name.endswith('.tar.gz'):
                ext_ok = True
            else:
                ext = lower_name.split('.')[-1]
                ext_ok = '.' + ext in ALLOWED_EXTS
            if ext_ok:
                entries.append({
                    "name": name,
                    "is_dir": False,
                    "path": full_path
                })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries

# ---------- API：文件列表 ----------
# 辅助函数：URL解码（改进版，支持 %2F 等）
def _url_decode(s):
    result = ''
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                hex_val = int(s[i+1:i+3], 16)
                result += chr(hex_val)
                i += 3
            except:
                result += s[i]
                i += 1
        else:
            result += s[i]
            i += 1
    return result

# ---------- API：测试流式响应（指定大小） ----------
@app.route("/api/test_stream_size")
def test_stream_size(request):
    print("[Web] 请求: /api/test_stream_size")
    try:
        # 从 args 获取 size 参数
        if hasattr(request, 'args') and request.args:
            size_str = request.args.get('size', '1024')
        else:
            # 回退到解析 query_string
            size_str = '1024'
            if hasattr(request, 'query_string') and request.query_string:
                qs = request.query_string
                for part in qs.split('&'):
                    if part.startswith('size='):
                        size_str = part[5:]
                        break
        try:
            total_size = int(size_str)
            if total_size <= 0:
                total_size = 1024
            elif total_size > 10 * 1024 * 1024:  # 限制最大 10MB
                total_size = 10 * 1024 * 1024
        except:
            total_size = 1024

        print("[Web] 生成测试数据流，大小: {} 字节".format(total_size))

        # 生成器：逐块产生数据
        def generate_data():
            CHUNK_SIZE = 1024
            remaining = total_size
            while remaining > 0:
                chunk_size = CHUNK_SIZE if remaining >= CHUNK_SIZE else remaining
                # 生成一个固定模式的块（便于观察）
                chunk = b'A' * chunk_size
                yield chunk
                remaining -= chunk_size

        # 返回流式响应
        return make_response(generate_data(), 200, {
            "Content-Type": "application/octet-stream",
            "X-Total-Size": str(total_size)
        })
    except Exception as e:
        print("[Web] /api/test_stream_size 异常:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- API：文件列表 ----------
@app.route("/api/files")
def files(request):
    print("[Web] 请求: /api/files")
    try:
        # 尝试从 request.params 获取 path（EasyWeb 通常支持）
        if hasattr(request, 'params') and request.params:
            path = request.params.get('path', '/sd')
            print("[Web] 从 params 获取路径:", path)
        else:
            # 回退到 query_string
            path = "/sd"
            if hasattr(request, 'query_string') and request.query_string:
                qs = request.query_string
                print("[Web] query_string:", qs)
                for part in qs.split('&'):
                    if part.startswith('path='):
                        path = part[5:]
                        break
        # URL解码
        decoded_path = _url_decode(path)
        print("[Web] 原始路径: {}, 解码后: {}".format(path, decoded_path))
        # 安全校验
        if not decoded_path.startswith('/sd/') and decoded_path != '/sd':
            return make_response({"error": "Invalid path"}, 400)
        if '..' in decoded_path:
            return make_response({"error": "Invalid path"}, 400)
        try:
            uos.stat(decoded_path)
        except:
            return make_response({"error": "Directory not found"}, 404)
        entries = _list_directory(decoded_path)
        return make_response({
            "current_path": decoded_path,
            "entries": entries
        }, 200)
    except Exception as e:
        print("[Web] /api/files 异常:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)


# ---------- API：文件夹专用路由 ----------
@app.route("/api/folder")
def folder(request):
    print("[Web] 请求: /api/folder")
    print("[Web] request.args:", getattr(request, 'args', None))
    print("[Web] request._args:", getattr(request, '_args', None))

    try:
        path = None
        # 尝试从 args 获取
        if hasattr(request, 'args') and request.args:
            path = request.args.get('path')
            print("[Web] 从 args 获取 path:", path)
        # 若失败，从 _args 获取
        if path is None and hasattr(request, '_args') and request._args:
            path = request._args.get('path')
            print("[Web] 从 _args 获取 path:", path)
        # 回退
        if path is None:
            print("[Web] 未获取到 path，使用默认 /sd")
            path = "/sd"
        else:
            path = _url_decode(path)
            print("[Web] 解码后的路径:", path)

        # 安全校验
        if not path.startswith('/sd/') and path != '/sd':
            return make_response({"error": "Invalid path"}, 400)
        if '..' in path:
            return make_response({"error": "Invalid path"}, 400)

        try:
            uos.stat(path)
        except:
            return make_response({"error": "Directory not found"}, 404)

        entries = _list_directory(path)
        print("[Web] 目录条目数:", len(entries))
        return make_response({
            "current_path": path,
            "entries": entries
        }, 200)
    except Exception as e:
        print("[Web] /api/folder 异常:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- API：删除文件 ----------
@app.route("/api/delete_file", methods=["POST"])
def delete_file(request):
    try:
        params = request.json if request.json else {}
        file_path = params.get("file_path")
        if not file_path:
            return make_response({"success": False, "error": "Missing file_path"}, 400)
        if not file_path.startswith('/sd/') or '..' in file_path:
            return make_response({"success": False, "error": "Invalid file path"}, 400)
        try:
            uos.stat(file_path)
        except:
            return make_response({"success": False, "error": "File not found"}, 404)
        uos.remove(file_path)
        print("[Web] 已删除文件: {}".format(file_path))
        return make_response({"success": True}, 200)
    except Exception as e:
        print("[Web] 删除文件失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：递归删除文件夹 ----------
@app.route("/api/delete_folder", methods=["POST"])
def delete_folder(request):
    try:
        params = request.json if request.json else {}
        folder_path = params.get("folder_path")
        if not folder_path:
            return make_response({"success": False, "error": "Missing folder_path"}, 400)
        if not folder_path.startswith('/sd/') or '..' in folder_path:
            return make_response({"success": False, "error": "Invalid folder path"}, 400)
        # 检查是否存在且是目录
        try:
            st = uos.stat(folder_path)
            if not (st[0] & 0x4000):
                return make_response({"success": False, "error": "Not a directory"}, 400)
        except:
            return make_response({"success": False, "error": "Folder not found"}, 404)
        # 递归删除
        def rmtree(path):
            try:
                items = uos.listdir(path)
            except:
                return
            for name in items:
                full = path + '/' + name
                try:
                    st2 = uos.stat(full)
                    if st2[0] & 0x4000:
                        rmtree(full)
                    else:
                        uos.remove(full)
                except:
                    pass
            try:
                uos.rmdir(path)
            except:
                pass
        rmtree(folder_path)
        print("[Web] 已删除文件夹: {}".format(folder_path))
        return make_response({"success": True}, 200)
    except Exception as e:
        print("[Web] 删除文件夹失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：归档文件夹 ----------
@app.route("/api/archive_folder", methods=["POST"])
def archive_folder(request):
    try:
        params = request.json if request.json else {}
        folder_path = params.get("folder_path")
        delete_after = params.get("delete_after", False)
        if not folder_path:
            return make_response({"success": False, "error": "Missing folder_path"}, 400)
        if not folder_path.startswith('/sd/') or '..' in folder_path:
            return make_response({"success": False, "error": "Invalid folder path"}, 400)
        # 检查是否存在且是目录
        try:
            st = uos.stat(folder_path)
            if not (st[0] & 0x4000):
                return make_response({"success": False, "error": "Not a directory"}, 400)
        except:
            return make_response({"success": False, "error": "Folder not found"}, 404)
        # 生成归档文件名（与文件夹同名，加上 .arc）
        if folder_path.endswith('/'):
            folder_path = folder_path[:-1]
        archive_path = folder_path + '.arc'
        # 调用归档函数
        success = create_archive(folder_path, archive_path, delete_source=delete_after)
        if success:
            print("[Web] 归档成功: {} -> {}".format(folder_path, archive_path))
            return make_response({"success": True, "archive_path": archive_path}, 200)
        else:
            return make_response({"success": False, "error": "Archive failed"}, 500)
    except Exception as e:
        print("[Web] 归档失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：解压归档文件 ----------
@app.route("/api/extract_archive", methods=["POST"])
def extract_archive(request):
    try:
        params = request.json if request.json else {}
        archive_path = params.get("archive_path")
        delete_after = params.get("delete_after", False)
        if not archive_path:
            return make_response({"success": False, "error": "Missing archive_path"}, 400)
        if not archive_path.startswith('/sd/') or '..' in archive_path:
            return make_response({"success": False, "error": "Invalid archive path"}, 400)
        # 检查文件是否存在
        try:
            uos.stat(archive_path)
        except:
            return make_response({"success": False, "error": "Archive not found"}, 404)
        # 确定目标目录（去掉 .arc 后缀，如果存在则用原名，否则用 原文件名_extracted）
        if archive_path.endswith('.arc'):
            target_dir = archive_path[:-4]
        else:
            target_dir = archive_path + '_extracted'
        # 调用解压函数
        extracted_files = extract_archive_util(archive_path, target_dir)
        if extracted_files:
            # 如果 delete_after 为 True，删除归档文件
            if delete_after:
                try:
                    uos.remove(archive_path)
                except:
                    pass
            print("[Web] 解压成功: {} -> {} ({} files)".format(archive_path, target_dir, len(extracted_files)))
            return make_response({"success": True, "target_dir": target_dir, "files_count": len(extracted_files)}, 200)
        else:
            return make_response({"success": False, "error": "Extract failed"}, 500)
    except Exception as e:
        print("[Web] 解压失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- 路由：查看 SD 卡文件 ----------
@app.route("/sd/<path>")
def sd_file(request):
    filename = request.match
    if isinstance(filename, tuple):
        filename = filename[0] if filename else ""
    print("[Web] 请求: /sd/{}".format(filename))
    try:
        if not filename:
            return make_response("Missing filename", 400)
        if '..' in filename or filename.startswith('/'):
            return make_response("Invalid path", 403)
        full_path = "/sd/" + filename

        # 检查是否为目录
        try:
            st = uos.stat(full_path)
            if st[0] & 0x4000:
                print("[Web] 拒绝访问目录: {}".format(full_path))
                return make_response("Cannot access directory", 403)
        except:
            pass

        # 确定 Content-Type 和是否为图片
        f_lower = filename.lower()
        ct = "application/octet-stream"
        is_image = False
        img_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico']
        for ext in img_exts:
            if len(f_lower) >= len(ext) and f_lower[-len(ext):] == ext:
                if ext in ('.jpg', '.jpeg'):
                    ct = "image/jpeg"
                elif ext == '.png':
                    ct = "image/png"
                elif ext == '.gif':
                    ct = "image/gif"
                elif ext == '.bmp':
                    ct = "image/bmp"
                elif ext == '.ico':
                    ct = "image/x-icon"
                is_image = True
                break

        # 设置 Content-Disposition：图片内联显示，其他附件下载
        if is_image:
            disposition = "inline"
        else:
            disposition = "attachment"

        # 使用 easyweb.send_file 流式传输，显式传递 mimetype
        print("[Web] 流式发送文件: {} (Content-Type: {}, Disposition: {})".format(full_path, ct, disposition))
        generator = easyweb.send_file(full_path, mimetype=ct)
        return make_response(generator, 200, {
            "Content-Type": ct,
            "Content-Disposition": "{}; filename=\"{}\"".format(disposition, filename)
        })

    except Exception as e:
        print("[Web] 文件读取失败: {}".format(e))
        sys.print_exception(e)
        return make_response("File not found", 404)

# ---------- API：设置 Wi-Fi ----------
@app.route("/api/set_wifi", methods=["POST"])
def set_wifi(request):
    try:
        params = request.json if request.json else {}
        ssid = params.get("ssid", "").strip()
        password = params.get("password", "").strip()
        if not ssid:
            return make_response({"success": False, "error": "SSID is required"}, 400)
        if not _save_wifi_config(ssid, password):
            return make_response({"success": False, "error": "Failed to save config"}, 500)
        success = _connect_wifi(ssid, password)
        if success:
            ip = _current_ip
            return make_response({"success": True, "ip": ip}, 200)
        else:
            return make_response({"success": False, "error": "Connection timeout"}, 200)
    except Exception as e:
        print("[Web] 设置 Wi-Fi 失败:", e)
        sys.print_exception(e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：重启设备 ----------
@app.route("/api/restart", methods=["POST"])
def restart(request):
    try:
        import machine
        print("[Web] 设备即将重启...")
        time.sleep_ms(500)
        machine.reset()
    except Exception as e:
        print("[Web] 重启失败:", e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- 启动入口 ----------
def start(host="0.0.0.0", port=80):
    ssid, password = _load_wifi_config()
    if ssid:
        print("[Web] 尝试自动连接 Wi-Fi: {}".format(ssid))
        if _connect_wifi(ssid, password):
            print("[Web] Wi-Fi 自动连接成功，IP: {}".format(_current_ip))
        else:
            print("[Web] Wi-Fi 自动连接失败")
    else:
        print("[Web] 未找到 Wi-Fi 配置，跳过自动连接")
    _clear_mode()
    print("Mode file cleared. Please select mode on first visit.")
    print("Starting EasyWeb server on http://{}:{}".format(host, port))
    app.run(host=host, port=port)

def stop():
    app.stop()