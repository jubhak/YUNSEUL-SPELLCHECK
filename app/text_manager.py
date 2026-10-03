import ctypes
from ctypes import wintypes
import time
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_CONTROL = 0x11
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_RIGHT = 0x27
KEYEVENTF_KEYUP = 0x0002

def _key_combo(mod, key):
    user32.keybd_event(mod, 0, 0, 0)
    user32.keybd_event(key, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(key, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(mod, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

class TextManager:
    @staticmethod
    def get_foreground_window():
        return user32.GetForegroundWindow()

    @staticmethod
    def get_text_from_active_input(target_hwnd=None, timeout=0.25):
        """
        현재 커서가 있는 입력창이나 선택된 영역에서 텍스트를 자동으로 추출합니다.
        1. 이미 텍스트가 드래그/선택되어 있으면 해당 선택 텍스트 복사 (Ctrl+C)
        2. 선택된 텍스트가 없으면, 현재 커서가 있는 입력창의 전체 텍스트 자동 선택 및 복사 (Ctrl+A -> Ctrl+C)
        반환값: (text, target_hwnd, selection_mode) - selection_mode: 'selected' 또는 'all'
        """
        if target_hwnd:
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.04)
        else:
            target_hwnd = user32.GetForegroundWindow()

        # Save previous clipboard
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        # Unique sentinel
        sentinel = f"__SPELL_GRAB_{time.time()}__"
        try:
            pyperclip.copy(sentinel)
        except Exception:
            pass

        # 1. First, check if text was already selected
        _key_combo(VK_CONTROL, VK_C)

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.02)
            try:
                clip = pyperclip.paste()
                if clip != sentinel and clip.strip():
                    return clip.strip(), target_hwnd, "selected"
            except Exception:
                pass

        # 2. If nothing was selected, automatically select all in the active input field
        _key_combo(VK_CONTROL, VK_A)
        time.sleep(0.03)
        _key_combo(VK_CONTROL, VK_C)

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.02)
            try:
                clip = pyperclip.paste()
                if clip != sentinel and clip.strip():
                    return clip.strip(), target_hwnd, "all"
            except Exception:
                pass

        # 3. If still nothing, restore old clipboard
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

        return "", target_hwnd, "none"

    @staticmethod
    def replace_selected_text(new_text: str, target_hwnd=None, selection_mode="selected"):
        """
        원래 입력창의 텍스트를 교정된 새 텍스트로 자동 치환합니다.
        """
        if not new_text:
            return False

        if target_hwnd:
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.06)

        # If it was 'all', re-select all just in case focus changed
        if selection_mode == "all":
            _key_combo(VK_CONTROL, VK_A)
            time.sleep(0.03)

        # Put new text in clipboard
        pyperclip.copy(new_text)
        time.sleep(0.03)

        # Simulate Ctrl+V
        _key_combo(VK_CONTROL, VK_V)

        return True

    @staticmethod
    def cancel_selection(target_hwnd=None, selection_mode="none"):
        """
        검사를 취소했을 때 전체 선택된 상태를 해제하고 커서를 맨 뒤로 이동시킵니다.
        """
        if selection_mode == "all" and target_hwnd:
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.02)
            # Press Right Arrow to unselect and place cursor at end
            user32.keybd_event(VK_RIGHT, 0, 0, 0)
            time.sleep(0.01)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def copy_to_clipboard(text: str):
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False
