from PyQt6 import QtWidgets, QtCore, QtGui

class FloatingMenu(QtWidgets.QWidget):
    spell_check_requested = QtCore.pyqtSignal(str)  # mode: 'auto', 'ocr', 'uia'
    open_editor_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool |
            QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Auto-hide timer
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        self._init_ui()

    def _init_ui(self):
        # Outer container layout
        outer_layout = QtWidgets.QHBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Main Card Frame
        self.card = QtWidgets.QFrame()
        self.card.setObjectName("cardFrame")
        self.card.setStyleSheet("""
            QFrame#cardFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F172A, stop:1 #1E293B);
                border: 1.5px solid #38BDF8;
                border-radius: 20px;
            }
        """)

        # Drop shadow
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        card_layout = QtWidgets.QHBoxLayout(self.card)
        card_layout.setContentsMargins(12, 5, 8, 5)
        card_layout.setSpacing(6)

        # 1. Main Action Button (Smart Auto: Caret / UIA / Selection)
        self.btn_check = QtWidgets.QPushButton("📝 맞춤법 검사")
        self.btn_check.setToolTip("커서 입력글 / 선택영역 / 커서 위치 단어를 자동 인식하여 검사합니다.")
        self.btn_check.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_check.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Malgun Gothic', sans-serif;
                padding: 4px 6px;
            }
            QPushButton:hover {
                color: #38BDF8;
            }
        """)
        self.btn_check.clicked.connect(lambda: self._on_action_clicked("auto"))
        card_layout.addWidget(self.btn_check)

        # Separator line
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep1.setStyleSheet("background-color: #334155; max-width: 1px; margin: 4px 2px;")
        card_layout.addWidget(sep1)

        # 2. 700px Native Korean OCR Button
        self.btn_ocr = QtWidgets.QPushButton("📸 700px OCR")
        self.btn_ocr.setToolTip("마우스 커서 중심 700px 화면 영역의 글자를 윈도우 네이티브 OCR로 광학 인식합니다.")
        self.btn_ocr.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_ocr.setStyleSheet("""
            QPushButton {
                background: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 12px;
                color: #38BDF8;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Malgun Gothic', sans-serif;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #0F172A;
            }
        """)
        self.btn_ocr.clicked.connect(lambda: self._on_action_clicked("ocr"))
        card_layout.addWidget(self.btn_ocr)

        # Separator line
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep2.setStyleSheet("background-color: #334155; max-width: 1px; margin: 4px 2px;")
        card_layout.addWidget(sep2)

        # 3. Close button
        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 12px;
                font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover {
                background: #334155;
                color: #FFFFFF;
            }
        """)
        self.btn_close.clicked.connect(self.hide)
        card_layout.addWidget(self.btn_close)

        outer_layout.addWidget(self.card)
        self.adjustSize()

    def popup_at(self, x, y, auto_hide_ms=5000):
        w = self.width() or 260
        h = self.height() or 46

        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        pos_x = x - (w // 2)
        pos_y = y - h - 14  # 14px above cursor

        if pos_x < 10:
            pos_x = 10
        elif pos_x + w > screen.width() - 10:
            pos_x = screen.width() - w - 10

        if pos_y < 10:
            pos_y = y + 25

        self.move(pos_x, pos_y)
        self.show()
        self.raise_()

        if auto_hide_ms > 0:
            self.hide_timer.start(auto_hide_ms)

    def _on_action_clicked(self, mode: str):
        self.hide_timer.stop()
        self.hide()
        self.spell_check_requested.emit(mode)
