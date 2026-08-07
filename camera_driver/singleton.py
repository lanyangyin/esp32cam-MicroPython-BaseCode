# camera_driver/singleton.py
"""摄像头单例管理"""
import time
import camera  # type: ignore
from .controller import CameraController
from config import debug_log


def _debug_log(msg):
    debug_log(msg, module="CameraCtrl")

_camera_instance = None

def get_camera(**init_kwargs):
    global _camera_instance
    if _camera_instance is not None:
        _debug_log("Return existing camera instance")
        return _camera_instance

    _debug_log("Creating camera instance...")
    try:
        _camera_instance = CameraController()
        _camera_instance.init(**init_kwargs)
        _debug_log("Camera initialized successfully")
        return _camera_instance
    except Exception as e:
        _debug_log("Creation failed: {}".format(e))
        try:
            camera.deinit()
        except:
            pass
        if _camera_instance is not None:
            try:
                _camera_instance.deinit()
            except:
                pass
            _camera_instance = None
        try:
            _camera_instance = CameraController()
            _camera_instance.init(**init_kwargs)
            _debug_log("Camera initialized on retry")
            return _camera_instance
        except Exception as e2:
            _debug_log("Retry failed: {}".format(e2))
            raise

def reset_camera():
    global _camera_instance
    try:
        camera.deinit()
        _debug_log("Force camera.deinit() called")
    except:
        pass
    if _camera_instance is not None:
        _debug_log("Resetting camera singleton")
        try:
            _camera_instance.deinit()
        except:
            pass
        _camera_instance = None