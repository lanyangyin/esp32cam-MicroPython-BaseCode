# config/debug.py
"""全局调试开关"""
DEBUG = True

def set_debug(enabled):
    global DEBUG
    DEBUG = enabled