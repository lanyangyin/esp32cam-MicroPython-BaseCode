# config/camera_model.py
"""
摄像头型号配置
用于决定使用哪套决策配置文件（flash_guide.json, retry_guide.json, quick_flash_guide.json）
支持从配置文件读取，若不存在则默认 ov3660。
"""
import uos
import json

# 默认型号（如果未配置）
DEFAULT_MODEL = "ov3660"

# 当前摄像头型号（运行时可变）
CAMERA_MODEL = DEFAULT_MODEL

# 型号配置文件路径（存放当前型号的文本文件）
MODEL_CONFIG_FILE = "/决策/model.txt"

# 配置文件的根目录（内部文件系统）
CONFIG_ROOT = "/决策"

def _ensure_dir(path):
    """逐级创建目录，若已存在则忽略"""
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

def _load_model_from_file():
    """从 model.txt 读取型号，若文件不存在则返回 None"""
    try:
        with open(MODEL_CONFIG_FILE, 'r') as f:
            model = f.read().strip()
            if model:
                return model
    except:
        pass
    return None

def _save_model_to_file(model):
    """保存型号到 model.txt"""
    try:
        _ensure_dir(CONFIG_ROOT)
        with open(MODEL_CONFIG_FILE, 'w') as f:
            f.write(model)
        return True
    except:
        return False

def get_camera_model():
    """获取当前摄像头型号（优先从文件读取，若无则使用内存中的值）"""
    global CAMERA_MODEL
    file_model = _load_model_from_file()
    if file_model is not None:
        CAMERA_MODEL = file_model
    else:
        # 如果文件不存在，但内存中已经有值（默认或 set 过），则写入文件
        if CAMERA_MODEL != DEFAULT_MODEL:
            _save_model_to_file(CAMERA_MODEL)
        else:
            # 使用默认值，并写入文件
            _save_model_to_file(DEFAULT_MODEL)
    return CAMERA_MODEL

def set_camera_model(model):
    """设置摄像头型号（同时写入文件，永久生效）"""
    global CAMERA_MODEL
    CAMERA_MODEL = model
    _save_model_to_file(model)

# 初始化时自动加载型号
get_camera_model()

def get_config_dir(model=None):
    """获取指定型号的配置目录路径，若不存在则逐级创建"""
    if model is None:
        model = get_camera_model()
    # 确保根目录存在
    _ensure_dir(CONFIG_ROOT)
    dir_path = "{}/{}".format(CONFIG_ROOT, model)
    _ensure_dir(dir_path)
    return dir_path

def get_config_path(filename, model=None):
    """获取指定型号的某个配置文件的完整路径"""
    dir_path = get_config_dir(model)
    return "{}/{}".format(dir_path, filename)