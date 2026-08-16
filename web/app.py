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

from advanced_photo import take_advanced_photo, burst_capture
from easyweb import EasyWeb, make_response, send_file, render_template
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
    # 使用 request.form 获取表单数据
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
            # 文件不存在，返回默认配置（与前端默认值对齐）
            default_config = {
                "flash_mode": "auto",
                "resolution": 1024,          # FRAME_XGA
                "whitebalance": 2,           # WB_CLOUDY
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
                "analysis_resolution": 320,  # FRAME_QVGA
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

# ---------- API：系统状态 ----------
@app.route("/api/status")
def status(request):
    print("[Web] 请求: /api/status")
    try:
        sd = get_sd_card()
        resolutions = _get_resolutions()   # 调用已有的分辨率获取函数
        status_data = {
            "model": CAMERA_MODEL,
            "sd_mounted": sd.mounted if sd else False,
            "timestamp": time.time(),
            "resolutions": resolutions,    # 添加这一行
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
        # brightness_threshold 已被移除

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
        # 调用连拍函数
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
        # 判断是否为目录
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
        # 安全校验：必须是以 /sd/ 开头，且不包含 '..' 路径穿越
        if not file_path.startswith('/sd/') or '..' in file_path:
            return make_response({"success": False, "error": "Invalid file path"}, 400)
        # 检查文件是否存在
        try:
            uos.stat(file_path)
        except:
            return make_response({"success": False, "error": "File not found"}, 404)
        # 删除文件
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
    # 修复：request.match 可能是元组，确保转为字符串
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
        # 手动检查后缀（不使用 endswith）
        f_lower = filename.lower()
        ct = "application/octet-stream"
        # 图片扩展名
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
        import network
        params = request.json if request.json else {}
        ssid = params.get("ssid", "").strip()
        password = params.get("password", "").strip()
        if not ssid:
            return make_response({"success": False, "error": "SSID is required"}, 400)
        # 连接 Wi-Fi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)
        # 等待连接（最多10秒）
        import time
        timeout = 10
        while timeout > 0:
            if wlan.isconnected():
                break
            time.sleep(1)
            timeout -= 1
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("[Web] Wi-Fi 连接成功，IP:", ip)
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
        # 先返回响应，再重启
        response = make_response({"success": True, "message": "Restarting..."}, 200)
        # 注意：需要异步发送响应后再重启，但 EasyWeb 是同步的，所以先发送再重启
        # 但 make_response 只是构造响应，实际发送在框架内部，我们可以先返回，然后立即重启
        # 但没法保证响应先发送，所以采用简单方式：直接触发重启，客户端会断开连接
        # 但为了友好，我们可以在重启前打印日志
        print("[Web] 设备即将重启...")
        # 延迟一点让响应发送出去
        import time
        time.sleep_ms(500)
        machine.reset()
    except Exception as e:
        print("[Web] 重启失败:", e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- 启动入口 ----------
def start(host="0.0.0.0", port=80):
    _clear_mode()
    print("Mode file cleared. Please select mode on first visit.")
    print("Starting EasyWeb server on http://{}:{}".format(host, port))
    app.run(host=host, port=port)

def stop():
    app.stop()