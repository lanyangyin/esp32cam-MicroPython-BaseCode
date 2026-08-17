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
import network  # 新增
import ujson    # 新增（MicroPython JSON 模块）

from advanced_photo import take_advanced_photo, burst_capture
from easyweb import EasyWeb, make_response
from photo import take_smart_photo, gray_quick_capture, gray_analyzer_capture
from video import RecorderTime
from sd_card import get_sd_card
from config import set_debug, CAMERA_MODEL
from config.camera_model import get_config_path

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
_current_ip = "0.0.0.0"  # 存储当前 IP

def _load_wifi_config():
    """从 SD 卡加载 Wi-Fi 配置，返回 (ssid, password)"""
    try:
        with open(WIFI_CONFIG_FILE, "r") as f:
            config = ujson.load(f)
            return config.get("ssid", ""), config.get("password", "")
    except:
        return "", ""

def _save_wifi_config(ssid, password):
    """保存 Wi-Fi 配置到 SD 卡"""
    try:
        config = {"ssid": ssid, "password": password}
        with open(WIFI_CONFIG_FILE, "w") as f:
            ujson.dump(config, f)
        return True
    except Exception as e:
        print("[Web] 保存 Wi-Fi 配置失败:", e)
        return False

def _connect_wifi(ssid, password):
    """尝试连接 Wi-Fi，成功返回 True，并设置 _current_ip"""
    global _current_ip
    if not ssid:
        return False
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # 如果已连接且 SSID 相同，则直接返回
    if wlan.isconnected():
        if wlan.config('essid') == ssid:
            _current_ip = wlan.ifconfig()[0]
            return True
        else:
            wlan.disconnect()
    # 开始连接
    wlan.connect(ssid, password)
    timeout = 10  # 等待 10 秒
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

# 注意：只接受 POST 方法
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
            }
            print("[Web] 配置不存在，返回默认")
            return make_response(default_config, 200)
    except Exception as e:
        print("[Web] 加载配置失败:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- API：系统状态（包含 IP） ----------
@app.route("/api/status")
def status(request):
    print("[Web] 请求: /api/status")
    try:
        sd = get_sd_card()
        resolutions = _get_resolutions()
        # 获取当前 IP
        wlan = network.WLAN(network.STA_IF)
        ip = wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"
        status_data = {
            "model": CAMERA_MODEL,
            "sd_mounted": sd.mounted if sd else False,
            "timestamp": time.time(),
            "resolutions": resolutions,
            "ip": ip,  # 添加 IP
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
        print("[Web] 参数: framesize={}, duration={}s, xclk={}".format(framesize, duration, xclk_freq))
        recorder = RecorderTime(
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

# ---------- 辅助函数：递归获取图片文件 ----------
def _get_files_recursive(path):
    """
    递归遍历目录，返回所有图片文件的完整路径。
    支持扩展名：.jpg, .jpeg, .ppm, .bmp, .raw
    """
    try:
        items = uos.listdir(path)
    except Exception:
        return []
    files = []
    for name in items:
        full = path + '/' + name if path != '/' else '/' + name
        try:
            st = uos.stat(full)
            is_dir = (st[0] & 0x4000) != 0
        except Exception:
            continue
        if is_dir:
            files.extend(_get_files_recursive(full))
        else:
            ext = name.split('.')[-1].lower()
            if ext in ('jpg', 'jpeg', 'ppm', 'bmp', 'raw'):
                files.append(full)
    return files

# ---------- API：文件列表 ----------
@app.route("/api/files")
def files(request):
    print("[Web] 请求: /api/files")
    try:
        sd = get_sd_card()
        file_list = []
        if sd and sd.mounted:
            root = sd.mount_point
            file_list = _get_files_recursive(root)
        print("[Web] 获取到 {} 个文件".format(len(file_list)))
        return make_response({"files": file_list}, 200)
    except Exception as e:
        print("[Web] /api/files 异常:", e)
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
        print("[Web] 尝试读取文件: {}".format(full_path))
        uos.stat(full_path)
        with open(full_path, "rb") as f:
            data = f.read()
        f_lower = filename.lower()
        ct = "application/octet-stream"
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
                break
        print("[Web] 文件大小: {} bytes, Content-Type: {}".format(len(data), ct))
        return make_response(data, 200, {"Content-Type": ct})
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
        # 保存配置
        if not _save_wifi_config(ssid, password):
            return make_response({"success": False, "error": "Failed to save config"}, 500)
        # 连接
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
        # 先发送响应再重启
        time.sleep_ms(500)
        machine.reset()
    except Exception as e:
        print("[Web] 重启失败:", e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- 启动入口 ----------
def start(host="0.0.0.0", port=80):
    # 尝试加载并自动连接 Wi-Fi
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