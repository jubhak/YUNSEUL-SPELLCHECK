import time
from collections import deque
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
        self._last_hotkey = 0
        # CPython deque append/popleft are atomic. Bounded, never block the hook.
        self._events = deque(maxlen=4)
        self._timer = QtCore.QTimer(self.signals)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._drain)

    def _drain(self):
        for _ in range(4):
            try:
                kind, x, y = self._events.popleft()
            except IndexError:
                break
            if kind == 'right':
                self.signals.right_clicked.emit(x, y)
            elif kind == 'drag':
                self.signals.drag_selected.emit(x, y)
            else:
                self.signals.hotkey_pressed.emit()

    def start(self):
        if self.mouse_listener:
            return
        self._timer.start()
        self.mouse_listener = mouse.Listener(
            on_click=self._on_click,
            win32_event_filter=lambda msg, data: not (data.flags & 0x01))
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(
                {'<alt>+s': self._on_hotkey},
                win32_event_filter=lambda msg, data: not (data.flags & 0x10))
            self.hotkey_listener.daemon = True
            self.hotkey_listener.start()
        except Exception as exc:
            print(f'[Hotkey] {exc}')

    def stop(self):
        self._timer.stop()
        self._events.clear()
        for listener in (self.mouse_listener, self.hotkey_listener):
            if listener:
                listener.stop()
        self.mouse_listener = self.hotkey_listener = None

    def set_config(self, config):
        self.config = dict(config)

    def _on_hotkey(self):
        now = time.monotonic()
        if now - self._last_hotkey >= 0.5:
            self._last_hotkey = now
            self._events.append(('hotkey', 0, 0))

    def _on_click(self, x, y, button, pressed):
        if pressed:
            if button == mouse.Button.left:
                self.down_pos = (x, y)
            return
        now = time.monotonic()
        if button == mouse.Button.right and self.config.get('enable_right_click', True):
            if now - self.last_trigger_time > 0.3:
                self.last_trigger_time = now
                self._events.append(('right', int(x), int(y)))
        elif button == mouse.Button.left and self.config.get('enable_drag_select', False):
            if abs(x - self.down_pos[0]) > 50 or abs(y - self.down_pos[1]) > 35:
                if now - self.last_trigger_time > 0.4:
                    self.last_trigger_time = now
                    self._events.append(('drag', int(x), int(y)))
