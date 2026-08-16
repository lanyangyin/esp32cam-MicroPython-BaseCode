# web/app.py
"""
使用 EasyWeb 框架的 Web 控制服务
"""

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
        err = f"<h1>Error loading page</h1><p>{e}</p>"
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
        print(f"[Web] 参数: framesize={framesize}, quality={quality}, mode={decision_mode}")
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
            print(f"[Web] 拍照成功: {saved_path}")
        else:
            result = {"success": False, "error": "Capture failed"}
            print("[Web] 拍照失败")
        return make_response(result, 200)
    except Exception as e:
        print("[Web] /api/capture 异常:", e)
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
        print(f"[Web] 参数: framesize={framesize}, duration={duration}s, xclk={xclk_freq}")
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
        print(f"[Web] 录像完成: {frames}帧, {elapsed:.2f}s")
        return make_response(result, 200)
    except Exception as e:
        print("[Web] /api/video 异常:", e)
        return make_response({"success": False, "error": str(e)}, 500)

# ---------- API：文件列表 ----------
@app.route("/api/files")
def files(request):
    print("[Web] 请求: /api/files")
    try:
        sd = get_sd_card()
        file_list = []
        if sd and sd.mounted:
            for f in sd.list_files():
                if f.lower().endswith(('.jpg', '.jpeg', '.ppm', '.bmp', '.raw')):
                    file_list.append(f)
        return make_response({"files": file_list}, 200)
    except Exception as e:
        print("[Web] /api/files 异常:", e)
        return make_response({"error": str(e)}, 500)

# ---------- 路由：下载 SD 卡文件 ----------
@app.route("/sd/<path:filename>")
def sd_file(request, filename):
    print(f"[Web] 请求: /sd/{filename}")
    # 安全防护
    if '..' in filename or filename.startswith('/'):
        return make_response("Invalid path", 403)
    full_path = "/sd/" + filename
    try:
        # 检查文件是否存在
        uos.stat(full_path)
        # 确定 MIME 类型
        if filename.lower().endswith(('.jpg', '.jpeg')):
            mime = "image/jpeg"
        else:
            mime = "application/octet-stream"
        # 使用 send_file 发送
        return send_file(full_path, mimetype=mime)
    except Exception as e:
        print(f"[Web] 文件下载失败: {e}")
        return make_response(f"File not found: {filename}", 404)

# ---------- 辅助函数 ----------
def _get_resolutions():
    """获取所有分辨率列表"""
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
    print(f"Starting EasyWeb server on http://{host}:{port}")
    app.run(host=host, port=port)

def stop():
    app.stop()