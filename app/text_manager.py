# -*- coding: utf-8 -*-
import ctypes
import time
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_MENU = 0x12       # Alt
VK_SHIFT = 0x10      # Shift
VK_CONTROL = 0x11    # Ctrl
VK_LWIN = 0x5B       # Win
VK_RWIN = 0x5C
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_RIGHT = 0x27
KEYEVENTF_KEYUP = 0x0002

def _clear_modifiers():
    """Alt, Shift, Ctrl, Win 등 눌려있는 보조키를 모두 해제하여 단축키 오작동을 방지합니다."""
    for vk in (VK_MENU, VK_SHIFT, VK_CONTROL, VK_LWIN, VK_RWIN):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

def _key_combo(mod, key):
    user32.keybd_event(mod, 0, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(key, 0, 0, 0)
    time.sleep(0.025)
    user32.keybd_event(key, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.015)
    user32.keybd_event(mod, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

class TextManager:
    @staticmethod
    def get_foreground_window():
        return user32.GetForegroundWindow()

    @staticmethod
    def force_foreground_window(hwnd):
        """윈도우 포커스 잠금(LockSetForegroundWindow)을 우회하여 목표 입력창에 강제로 포커스를 부여합니다."""
        if not hwnd or not user32.IsWindow(hwnd):
            return False
        if user32.GetForegroundWindow() == hwnd:
            return True

        current_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        attached = False
        if fg_thread and target_thread and fg_thread != target_thread:
            user32.AttachThreadInput(current_thread, fg_thread, True)
            user32.AttachThreadInput(current_thread, target_thread, True)
            attached = True

        # Alt key trick to bypass Windows focus restriction
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        if attached:
            user32.AttachThreadInput(current_thread, fg_thread, False)
            user32.AttachThreadInput(current_thread, target_thread, False)

        time.sleep(0.05)
        return True

    @staticmethod
    def get_text_from_active_input(target_hwnd=None, timeout=0.35):
        """
        현재 커서가 있는 활성 입력창(프롬프트)이나 선택 영역에서 텍스트를 안정적으로 캡처합니다.
        1. 이미 드래그된 선택 영역이 있으면 Ctrl+C로 즉시 복사 ('selected')
        2. 선택된 글이 없고 커서만 있는 경우, Ctrl+A -> Ctrl+C 로 전체 문장 복사 ('all')
           (복사 직후 오른쪽 화살표 키를 보내 선택을 해제하여 사용자의 작성 화면을 그대로 유지)
        """
        if target_hwnd:
            TextManager.force_foreground_window(target_hwnd)
        else:
            target_hwnd = user32.GetForegroundWindow()

        _clear_modifiers()

        # 기존 클립보드 백업
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        sentinel = f"__SPELL_GRAB_{time.time()}_{id(target_hwnd)}__"
        try:
            pyperclip.copy(sentinel)
            time.sleep(0.03)
        except Exception:
            pass

        # 1차 시도: 사용자가 이미 드래그해 둔 텍스트가 있는지 확인 (Ctrl+C)
        _key_combo(VK_CONTROL, VK_C)
        start = time.time()
        while time.time() - start < 0.15:
            time.sleep(0.02)
            try:
                clip = pyperclip.paste()
                if clip != sentinel and clip.strip():
                    return clip.strip(), target_hwnd, "selected"
            except Exception:
                pass

        # 2차 시도: 선택 영역이 없으면 입력창(프롬프트) 전체 선택 복사 (Ctrl+A -> Ctrl+C)
        _key_combo(VK_CONTROL, VK_A)
        time.sleep(0.03)
        _key_combo(VK_CONTROL, VK_C)

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.02)
            try:
                clip = pyperclip.paste()
                if clip != sentinel and clip.strip():
                    # 캡처 성공 시, 사용자의 입력창이 파랗게 전체 선택된 상태로 남지 않도록 우측 화살표로 해제
                    user32.keybd_event(VK_RIGHT, 0, 0, 0)
                    time.sleep(0.01)
                    user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)
                    return clip.strip(), target_hwnd, "all"
            except Exception:
                pass

        # 아무것도 캡처되지 않았을 경우, 기존 클립보드 원복
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

        return "", target_hwnd, "none"

    @staticmethod
    def replace_selected_text(new_text: str, target_hwnd=None, selection_mode="selected"):
        """원래 입력창의 텍스트를 교정된 새 텍스트로 자동 치환합니다."""
        if not new_text:
            return False

        if target_hwnd:
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            TextManager.force_foreground_window(target_hwnd)
            time.sleep(0.05)

        _clear_modifiers()

        # 전체 입력창 모드였던 경우 다시 전체 선택
        if selection_mode == "all":
            _key_combo(VK_CONTROL, VK_A)
            time.sleep(0.03)

        # 교정문 클립보드 복사 후 붙여넣기
        try:
            pyperclip.copy(new_text)
            time.sleep(0.04)
        except Exception:
            pass

        _key_combo(VK_CONTROL, VK_V)
        return True

    @staticmethod
    def cancel_selection(target_hwnd=None, selection_mode="none"):
        """검사를 취소했을 때 전체 선택된 상태를 해제하고 커서를 맨 뒤로 이동시킵니다."""
        if selection_mode == "all" and target_hwnd:
            TextManager.force_foreground_window(target_hwnd)
            time.sleep(0.02)
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
