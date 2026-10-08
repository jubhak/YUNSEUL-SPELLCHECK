import os
import json
import pyperclip
from PyQt6 import QtWidgets, QtCore, QtGui

from app.checker import SpellCheckerEngine
from app.text_manager import TextManager
from app.cursor_recognizer import CursorTextRecognizer
from app.mouse_hook import MouseHookManager
from app.floating_menu import FloatingMenu
from app.guideline_popup import GuidelinePopup
from app.main_window import MainWindow
from app.tray_icon import SystemTrayIcon

import sys

def get_config_path() -> str:
    # 1. Portable mode: next to exe
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        portable_cfg = os.path.join(exe_dir, "config.json")
        if os.path.exists(portable_cfg):
            return portable_cfg
    else:
        dev_cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        if os.path.exists(dev_cfg):
            return dev_cfg

    # 2. Persistent Windows AppData directory
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    cfg_dir = os.path.join(appdata, "YUNSEUL-SPELLCHECK")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, "config.json")

DEFAULT_CONFIG = {
    "enable_right_click": True,
    "enable_drag_select": False,  # Default False to prevent menu from popping up on ordinary mouse drags
    "close_to_tray": True,
    "start_minimized": False,
    "ocr_width": 700,
    "ocr_height": 140
}

class AppController(QtCore.QObject):
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app
        self.config = self._load_config()

        # Engine & Recognizer
        self.engine = SpellCheckerEngine()
        self.recognizer = CursorTextRecognizer(
            ocr_width=self.config.get("ocr_width", 700),
            ocr_height=self.config.get("ocr_height", 140)
        )

        # Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        self.app_icon = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
        self.app.setWindowIcon(self.app_icon)

        # Windows and Widgets
        self.floating_menu = FloatingMenu()
        self.guideline_popup = GuidelinePopup()
        self.main_window = MainWindow(self.engine, self.config)
        self.tray_icon = SystemTrayIcon(self.app_icon, config=self.config)

        # Hook Manager
        self.hook_manager = MouseHookManager(config=self.config)
        self.last_target_hwnd = None
        self.last_cursor_pos = (0, 0)

        self._connect_signals()

    def _load_config(self) -> dict:
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cfg = DEFAULT_CONFIG.copy()
                    cfg.update(data)
                    return cfg
            except Exception as e:
                print(f"[Config] Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        cfg_path = get_config_path()
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def _connect_signals(self):
        # Mouse Hook Signals
        self.hook_manager.signals.right_clicked.connect(self._on_mouse_right_click)
        self.hook_manager.signals.drag_selected.connect(self._on_mouse_drag_select)
        self.hook_manager.signals.hotkey_pressed.connect(self._on_hotkey)

        # Floating Menu (mode: 'auto' | 'ocr' | 'uia')
        self.floating_menu.spell_check_requested.connect(self._trigger_spell_check)

        # Guideline Popup
        self.guideline_popup.open_editor_requested.connect(self.main_window.load_text)

        # Main Window
        self.main_window.settings_changed.connect(self._on_settings_changed)

        # Tray Icon
        self.tray_icon.open_main_requested.connect(self._show_main_window)
        self.tray_icon.open_settings_requested.connect(self._show_settings)
        self.tray_icon.check_clipboard_requested.connect(self._check_clipboard)
        self.tray_icon.toggle_right_click.connect(self._on_toggle_right_click)
        self.tray_icon.toggle_drag_select.connect(self._on_toggle_drag_select)
        self.tray_icon.exit_requested.connect(self.quit_app)

    def start(self):
        self.tray_icon.show()
        self.hook_manager.start()

        if not self.config.get('start_minimized', False):
            self.main_window.show()

    def _is_own_window(self, hwnd) -> bool:
        if not hwnd:
            return False
        try:
            own_hwnds = {
                int(self.main_window.winId()),
                int(self.floating_menu.winId()),
                int(self.guideline_popup.winId())
            }
            if int(hwnd) in own_hwnds:
                return True
        except Exception:
            pass
        return False

    def _on_mouse_right_click(self, x, y):
        # Strict guard: ignore if right click trigger is disabled
        if not self.config.get('enable_right_click', True):
            return
        hwnd = TextManager.get_foreground_window()
        if self._is_own_window(hwnd):
            return
        self.last_cursor_pos = (x, y)
        self.last_target_hwnd = hwnd
        self.floating_menu.popup_at(x, y)

    def _on_mouse_drag_select(self, x, y):
        # Strict guard: ignore if drag select trigger is disabled
        if not self.config.get('enable_drag_select', False):
            return
        hwnd = TextManager.get_foreground_window()
        if self._is_own_window(hwnd):
            return
        self.last_cursor_pos = (x, y)
        self.last_target_hwnd = hwnd
        self.floating_menu.popup_at(x, y)

    def _on_hotkey(self):
        self.last_cursor_pos = (QtGui.QCursor.pos().x(), QtGui.QCursor.pos().y())
        self.last_target_hwnd = TextManager.get_foreground_window()
        self._trigger_spell_check("auto")

    def _trigger_spell_check(self, mode: str = "auto"):
        x, y = self.last_cursor_pos
        target_hwnd = self.last_target_hwnd
        selection_mode = "none"

        # 1. If explicit OCR mode requested:
        if mode == "ocr":
            ocr_res = self.recognizer.get_text_via_ocr(x, y, width=700)
            text = ocr_res.get('text', '')
            selection_mode = "none"
        else:
            # 2. Smart Hybrid Auto-Detection:
            # - Existing selection
            # - Input field typing (Caret)
            # - UI Automation under cursor (RangeFromPoint)
            # - 700px Screen OCR fallback
            detect_res = self.recognizer.smart_detect(x, y, target_hwnd=target_hwnd)
            text = detect_res.get('text', '')
            selection_mode = detect_res.get('selection_mode', 'none')
            if detect_res.get('target_hwnd'):
                target_hwnd = detect_res.get('target_hwnd')

        # Fallback to clipboard if nothing detected
        if not text:
            try:
                clip_text = pyperclip.paste().strip()
                if clip_text and len(clip_text) < 500:
                    text = clip_text
                    selection_mode = "none"
            except Exception:
                pass

        if not text:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            QtWidgets.QMessageBox.information(
                self.main_window,
                "윤슬 맞춤법 검사기",
                "마우스 커서 근처에서 텍스트를 감지하지 못했습니다.\n검사할 문장을 입력창에 입력하시거나 직접 입력해 주세요."
            )
            return

        # Perform check
        result = self.engine.check(text)

        # Show Guideline Popup
        self.guideline_popup.show_guidelines(
            result,
            target_hwnd=target_hwnd,
            selection_mode=selection_mode
        )

    def _check_clipboard(self):
        try:
            text = pyperclip.paste().strip()
            if not text:
                QtWidgets.QMessageBox.information(None, "알림", "클립보드에 복사된 텍스트가 없습니다.")
                return
            result = self.engine.check(text)
            self.guideline_popup.show_guidelines(result, target_hwnd=None, selection_mode="none")
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "오류", f"클립보드 검사 중 오류: {e}")

    def _show_main_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _show_settings(self):
        self.main_window.tab_widget.setCurrentIndex(1)
        self._show_main_window()

    def _on_toggle_right_click(self, enabled):
        self.config['enable_right_click'] = enabled
        self.hook_manager.set_config(self.config)
        self.main_window.chk_right_click.blockSignals(True)
        self.main_window.chk_right_click.setChecked(enabled)
        self.main_window.chk_right_click.blockSignals(False)
        self._save_config()

    def _on_toggle_drag_select(self, enabled):
        self.config['enable_drag_select'] = enabled
        self.hook_manager.set_config(self.config)
        self.main_window.chk_drag_select.blockSignals(True)
        self.main_window.chk_drag_select.setChecked(enabled)
        self.main_window.chk_drag_select.blockSignals(False)
        self._save_config()

    def _on_settings_changed(self, new_config):
        self.config.update(new_config)
        self.hook_manager.set_config(self.config)
        self.tray_icon.action_right_click.setChecked(self.config.get('enable_right_click', True))
        self.tray_icon.action_drag.setChecked(self.config.get('enable_drag_select', False))
        self._save_config()

    def quit_app(self):
        self.hook_manager.stop()
        self.tray_icon.hide()
        self._save_config()
        self.app.quit()
