import time
from pynput import mouse, keyboard
from PyQt6 import QtCore

class HookSignalEmitter(QtCore.QObject):
    right_clicked = QtCore.pyqtSignal(int, int)
    drag_selected = QtCore.pyqtSignal(int, int)
    hotkey_pressed = QtCore.pyqtSignal()

class MouseHookManager:
    def __init__(self, config=None):
        self.config = config or {}
        self.signals = HookSignalEmitter()
        self.mouse_listener = None
        self.hotkey_listener = None
        self.down_pos = (0, 0)
        self.last_trigger_time = 0

    def start(self):
        # 1. Mouse Hook
        self.mouse_listener = mouse.Listener(
            on_click=self._on_click
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

        # 2. Keyboard Global Hotkey: Alt + S
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<alt>+s': self._on_hotkey
            })
            self.hotkey_listener.daemon = True
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[Hotkey] Error starting hotkey listener: {e}")

    def stop(self):
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
            self.mouse_listener = None

        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None

    def set_config(self, config: dict):
        self.config = config

    def _on_hotkey(self):
        self.signals.hotkey_pressed.emit()

    def _on_click(self, x, y, button, pressed):
        if pressed:
            if button == mouse.Button.left:
                self.down_pos = (x, y)
        else:
            # Button released
            if button == mouse.Button.right:
                if not self.config.get('enable_right_click', True):
                    return
                now = time.time()
                if now - self.last_trigger_time > 0.3:
                    self.last_trigger_time = now
                    self.signals.right_clicked.emit(int(x), int(y))
            elif button == mouse.Button.left:
                if not self.config.get('enable_drag_select', False):
                    return
                dx = abs(x - self.down_pos[0])
                dy = abs(y - self.down_pos[1])
                # Genuine drag threshold (ignore micro movements while clicking)
                if (dx > 50 or dy > 35):
                    now = time.time()
                    if now - self.last_trigger_time > 0.4:
                        self.last_trigger_time = now
                        self.signals.drag_selected.emit(int(x), int(y))
