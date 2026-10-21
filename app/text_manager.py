# -*- coding: utf-8 -*-
"""Non-invasive window context and clipboard helpers (no input injection)."""
import ctypes
from ctypes import wintypes
import pyperclip

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                ('hwndActive', wintypes.HWND), ('hwndFocus', wintypes.HWND),
                ('hwndCapture', wintypes.HWND), ('hwndMenuOwner', wintypes.HWND),
                ('hwndMoveSize', wintypes.HWND), ('hwndCaret', wintypes.HWND),
                ('rcCaret', wintypes.RECT)]


user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.GetGUIThreadInfo.restype = wintypes.BOOL


class TextManager:
    @staticmethod
    def get_foreground_window():
        return user32.GetForegroundWindow()

    @staticmethod
    def capture_context(hwnd=None):
        hwnd = hwnd or user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        thread = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(info)
        ok = user32.GetGUIThreadInfo(thread, ctypes.byref(info)) if thread else False
        return {'hwnd': hwnd, 'pid': pid.value,
                'focus_hwnd': info.hwndFocus if ok else None}

    @staticmethod
    def force_foreground_window(hwnd):
        # Never join input queues or force focus away from the user's application.
        return bool(hwnd and user32.IsWindow(hwnd) and user32.GetForegroundWindow() == hwnd)

    @staticmethod
    def get_text_from_active_input(target_hwnd=None, timeout=0.35):
        # Compatibility only. All actual capture runs in the killable worker.
        return '', target_hwnd, 'none'

    @staticmethod
    def replace_selected_text(new_text, target_hwnd=None, selection_mode='none'):
        # A UIA read does NOT select text. Pasting now could insert at a stale caret
        # or replace the entire document. Use explicit Copy + manual selection.
        return False

    @staticmethod
    def cancel_selection(target_hwnd=None, selection_mode='none'):
        return None  # Capture never changes the user's selection.

    @staticmethod
    def copy_to_clipboard(text):
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False
