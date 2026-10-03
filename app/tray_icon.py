from PyQt6 import QtWidgets, QtCore, QtGui

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    open_main_requested = QtCore.pyqtSignal()
    open_settings_requested = QtCore.pyqtSignal()
    check_clipboard_requested = QtCore.pyqtSignal()
    toggle_right_click = QtCore.pyqtSignal(bool)
    toggle_drag_select = QtCore.pyqtSignal(bool)
    exit_requested = QtCore.pyqtSignal()

    def __init__(self, icon: QtGui.QIcon, parent=None, config=None):
        super().__init__(icon, parent)
        self.config = config or {}
        self.setToolTip("윤슬 맞춤법 & 띄어쓰기 검사기")

        self._create_menu()
        self.activated.connect(self._on_tray_activated)

    def _create_menu(self):
        menu = QtWidgets.QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Malgun Gothic', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px;
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #0284C7;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E8F0;
                margin: 4px 6px;
            }
        """)

        action_open = menu.addAction("📝 맞춤법 검사기 열기")
        action_open.triggered.connect(self.open_main_requested.emit)

        action_clip = menu.addAction("📋 클립보드 즉시 검사")
        action_clip.triggered.connect(self.check_clipboard_requested.emit)

        menu.addSeparator()

        self.action_right_click = menu.addAction("✔️ 마우스 우클릭 메뉴 켜기")
        self.action_right_click.setCheckable(True)
        self.action_right_click.setChecked(self.config.get('enable_right_click', True))
        self.action_right_click.triggered.connect(self._on_toggle_right_click)

        self.action_drag = menu.addAction("✔️ 텍스트 드래그 퀵버튼 켜기")
        self.action_drag.setCheckable(True)
        self.action_drag.setChecked(self.config.get('enable_drag_select', True))
        self.action_drag.triggered.connect(self._on_toggle_drag)

        menu.addSeparator()

        action_settings = menu.addAction("⚙️ 환경 설정")
        action_settings.triggered.connect(self.open_settings_requested.emit)

        action_exit = menu.addAction("🚪 종료")
        action_exit.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(menu)

    def _on_toggle_right_click(self, checked):
        self.config['enable_right_click'] = checked
        self.toggle_right_click.emit(checked)

    def _on_toggle_drag(self, checked):
        self.config['enable_drag_select'] = checked
        self.toggle_drag_select.emit(checked)

    def _on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_main_requested.emit()
