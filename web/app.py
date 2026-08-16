# web/app.py
"""
使用 EasyWeb 框架的 Web 控制服务
"""

import sys
import time
import camera
import uos
from easyweb import EasyWeb, make_response, send_file, render_template
from photo import take_smart_photo, gray_quick_capture, gray_analyzer_capture
from video import RecorderTime
from sd_card import get_sd_card
from config import set_debug, CAMERA_MODEL
from config.camera_model import get_config_path

set_debug(True)

app = EasyWeb()

# ---------- 主页 ----------
@app.route("/")
def index(request):
    print("[Web] 请求: /")
    try:
        with open("/web/static/index.html", "r") as f:
            html = f.read()
        return make_response(html, 200)
    except Exception as e:
        print("[Web] / 异常:", e)
        sys.print_exception(e)
        err = "<h1>Error loading page</h1><p>{}</p>".format(e)
        return make_response(err, 500)

# ---------- API：系统状态 ----------
@app.route("/api/status")
def status(request):
    print("[Web] 请求: /api/status")
    try:
        sd = get_sd_card()
        status_data = {
            "model": CAMERA_MODEL,
            "sd_mounted": sd.mounted if sd else False,
            "resolutions": _get_resolutions(),
            "timestamp": time.time()
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
        framesize = params.get("framesize", camera.FRAME_XGA)
        quality = params.get("quality", 10)
        decision_mode = params.get("decision_mode", "quick")
        print("[Web] 参数: framesize={}, quality={}, mode={}".format(framesize, quality, decision_mode))
        saved_path, w, h, brightness = take_smart_photo(
            analysis_framesize=camera.FRAME_QVGA,
            photo_framesize=framesize,
            quality=quality,
            decision_mode=decision_mode,
            retry_analysis_limit=3,
            retry_capture_limit=3
        )
        if saved_path:
            avg = brightness.get('average_brightness', 0) if brightness else 0
            result = {
                "success": True,
                "path": saved_path,
                "width": w,
                "height": h,
                "brightness": avg
            }
            print("[Web] 拍照成功: {}".format(saved_path))
        else:
            result = {"success": False, "error": "Capture failed"}
            print("[Web] 拍照失败")
        return make_response(result, 200)
    except Exception as e:
        print("[Web] /api/capture 异常:", e)
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

# ---------- API：文件列表 ----------
@app.route("/api/files")
def files(request):
    print("[Web] 请求: /api/files")
    try:
        sd = get_sd_card()
        file_list = []
        if sd and sd.mounted:
            raw_files = sd.list_files()
            print("[Web] 原始文件列表类型: {} 内容: {}".format(type(raw_files), raw_files))
            extensions = ['.jpg', '.jpeg', '.ppm', '.bmp', '.raw']
            for f in raw_files:
                f_str = str(f)
                f_lower = f_str.lower()
                is_image = False
                for ext in extensions:
                    if len(f_lower) >= len(ext) and f_lower[-len(ext):] == ext:
                        is_image = True
                        break
                if is_image:
                    file_list.append(f_str)
        print("[Web] 过滤后文件数: {}".format(len(file_list)))
        return make_response({"files": file_list}, 200)
    except Exception as e:
        print("[Web] /api/files 异常:", e)
        sys.print_exception(e)
        return make_response({"error": str(e)}, 500)

# ---------- 路由：查看 SD 卡文件（在浏览器中显示，而不是下载） ----------
@app.route("/sd/<path>")
def sd_file(request):
    filename = request.match  # EasyWeb 会将匹配的路径部分存入 request.match
    print("[Web] 请求: /sd/{}".format(filename))
    try:
        if not filename:
            print("[Web] 文件名缺失")
            return make_response("Missing filename", 400)
        if '..' in filename or filename.startswith('/'):
            print("[Web] 非法路径: {}".format(filename))
            return make_response("Invalid path", 403)
        full_path = "/sd/" + filename
        print("[Web] 尝试读取文件: {}".format(full_path))
        # 检查文件是否存在
        uos.stat(full_path)
        # 读取文件内容
        with open(full_path, "rb") as f:
            data = f.read()
        # 判断文件类型
        f_lower = filename.lower()
        # 图片扩展名
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico']
        is_image = False
        for ext in image_exts:
            if len(f_lower) >= len(ext) and f_lower[-len(ext):] == ext:
                is_image = True
                break
        if is_image:
            # 根据扩展名设置 MIME 类型
            if f_lower.endswith('.png'):
                ct = "image/png"
            elif f_lower.endswith('.gif'):
                ct = "image/gif"
            elif f_lower.endswith('.bmp'):
                ct = "image/bmp"
            elif f_lower.endswith('.ico'):
                ct = "image/x-icon"
            else:
                ct = "image/jpeg"
        else:
            # 非图片文件，作为普通文件下载
            ct = "application/octet-stream"
        print("[Web] 文件存在，大小: {} bytes, Content-Type: {}".format(len(data), ct))
        # 返回响应，通过 headers 参数设置 Content-Type
        return make_response(data, 200, {"Content-Type": ct})
    except Exception as e:
        print("[Web] 文件读取失败: {}".format(e))
        sys.print_exception(e)
        return make_response("File not found: {}".format(filename), 404)

# ---------- 辅助函数 ----------
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

# ---------- 启动入口 ----------
def start(host="0.0.0.0", port=80):
    print("Starting EasyWeb server on http://{}:{}".format(host, port))
    app.run(host=host, port=port)

def stop():
    app.stop()