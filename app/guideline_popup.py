from PyQt6 import QtWidgets, QtCore, QtGui
from app.text_manager import TextManager

class GuidelinePopup(QtWidgets.QWidget):
    open_editor_requested = QtCore.pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.target_hwnd = None
        self.selection_mode = "selected"
        self.current_result = None
        self.drag_position = QtCore.QPoint()
        self.was_replaced = False

        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(540, 620)

        # Outer layout for drop shadow
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Main Card Container
        self.card = QtWidgets.QFrame()
        self.card.setObjectName("popupCard")
        self.card.setStyleSheet("""
            QFrame#popupCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)

        # Drop shadow
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 18)
        card_layout.setSpacing(10)

        # 1. Header (Title, Pin, Close)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_icon = QtWidgets.QLabel("✨")
        lbl_icon.setStyleSheet("font-size: 18px;")
        header_layout.addWidget(lbl_icon)

        self.lbl_title = QtWidgets.QLabel("맞춤법 & 띄어쓰기 가이드라인")
        self.lbl_title.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
            font-family: 'Malgun Gothic', sans-serif;
        """)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        # Toast label for copy feedback
        self.lbl_toast = QtWidgets.QLabel("")
        self.lbl_toast.setStyleSheet("""
            color: #059669;
            font-size: 12px;
            font-weight: bold;
            background: #D1FAE5;
            padding: 2px 8px;
            border-radius: 6px;
        """)
        self.lbl_toast.hide()
        header_layout.addWidget(self.lbl_toast)

        # Close button
        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                border: none;
                border-radius: 14px;
                color: #64748B;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E2E8F0;
                color: #0F172A;
            }
        """)
        btn_close.clicked.connect(self._on_close)
        header_layout.addWidget(btn_close)

        card_layout.addLayout(header_layout)

        # 2. Status Banner & Category Badges
        self.banner_frame = QtWidgets.QFrame()
        self.banner_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        banner_layout = QtWidgets.QHBoxLayout(self.banner_frame)
        banner_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_status = QtWidgets.QLabel("검사 결과를 불러오는 중...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
        banner_layout.addWidget(self.lbl_status)
        banner_layout.addStretch()

        self.badge_box = QtWidgets.QHBoxLayout()
        self.badge_box.setSpacing(6)
        banner_layout.addLayout(self.badge_box)

        card_layout.addWidget(self.banner_frame)

        # 3. Original Text Banner (현재 입력창에서 가져온 글)
        lbl_orig_title = QtWidgets.QLabel("현재 입력창의 원문 글:")
        lbl_orig_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B;")
        card_layout.addWidget(lbl_orig_title)

        self.lbl_orig_box = QtWidgets.QLabel("")
        self.lbl_orig_box.setWordWrap(True)
        self.lbl_orig_box.setStyleSheet("""
            background-color: #FFF1F2;
            border: 1px solid #FECDD3;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
            color: #9F1239;
            font-family: 'Malgun Gothic', sans-serif;
            max-height: 48px;
        """)
        card_layout.addWidget(self.lbl_orig_box)

        # 4. Corrected Text Preview Box
        lbl_preview_title = QtWidgets.QLabel("교정된 문장 (추천):")
        lbl_preview_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #166534;")
        card_layout.addWidget(lbl_preview_title)

        self.text_preview = QtWidgets.QTextEdit()
        self.text_preview.setFixedHeight(75)
        self.text_preview.setReadOnly(True)
        self.text_preview.setStyleSheet("""
            QTextEdit {
                background-color: #F0FDF4;
                border: 1.5px solid #86EFAC;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                color: #166534;
                font-family: 'Malgun Gothic', sans-serif;
                line-height: 1.4;
            }
        """)
        card_layout.addWidget(self.text_preview)

        # 5. Detailed Guidelines Scroll Area
        lbl_guide_title = QtWidgets.QLabel("상세 교정 내역 및 맞춤법 가이드:")
        lbl_guide_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B;")
        card_layout.addWidget(lbl_guide_title)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 3px;
            }
        """)

        self.scroll_content = QtWidgets.QWidget()
        self.items_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(8, 8, 8, 8)
        self.items_layout.setSpacing(6)
        self.items_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)

        card_layout.addWidget(self.scroll_area)

        # 6. Bottom Action Buttons
        btn_bar = QtWidgets.QHBoxLayout()
        btn_bar.setSpacing(8)

        # Replace in original active app
        self.btn_replace = QtWidgets.QPushButton("⚡ 입력창에 바로 적용")
        self.btn_replace.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_replace.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_replace.clicked.connect(self._on_replace_clicked)
        btn_bar.addWidget(self.btn_replace)

        # Copy button
        self.btn_copy = QtWidgets.QPushButton("📋 교정문 복사")
        self.btn_copy.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        btn_bar.addWidget(self.btn_copy)

        # Open in editor
        self.btn_editor = QtWidgets.QPushButton("🔍 상세 편집기")
        self.btn_editor.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_editor.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px 12px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_editor.clicked.connect(self._on_editor_clicked)
        btn_bar.addWidget(self.btn_editor)

        card_layout.addLayout(btn_bar)

        outer_layout.addWidget(self.card)

    def set_result(self, result: dict, target_hwnd=None, selection_mode="selected"):
        self.current_result = result
        self.target_hwnd = target_hwnd
        self.selection_mode = selection_mode
        self.was_replaced = False

        # Clear badges
        while self.badge_box.count():
            item = self.badge_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear items
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        err_count = result.get('err_count', 0)
        original = result.get('original', '')
        corrected = result.get('corrected', '')
        counts = result.get('counts', {})

        # Display original and corrected
        self.lbl_orig_box.setText(original if original else "(비어 있음)")
        self.text_preview.setPlainText(corrected)

        if err_count == 0:
            self.lbl_status.setText("🎉 맞춤법 및 띄어쓰기가 완벽합니다!")
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: 700; color: #059669;")
            self.btn_replace.setEnabled(False)

            clean_lbl = QtWidgets.QLabel("오류가 발견되지 않았습니다.")
            clean_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 20px; text-align: center;")
            self.items_layout.insertWidget(0, clean_lbl)

        else:
            self.lbl_status.setText(f"⚠️ 총 {err_count}개의 교정 항목이 발견되었습니다.")
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: 700; color: #DC2626;")
            self.btn_replace.setEnabled(False)
            self.btn_replace.setToolTip("안전 모드: 교정문을 복사한 뒤 원문의 해당 문장만 선택하여 붙여넣어 주세요.")

            # Badges
            if result.get('is_offline'):
                offline_badge = QtWidgets.QLabel("📡 오프라인 규칙 검사")
                offline_badge.setStyleSheet("""
                    background-color: #FEF3C7;
                    color: #B45309;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 2px 7px;
                    border-radius: 4px;
                """)
                self.badge_box.addWidget(offline_badge)

            colors = {
                '맞춤법': ('#FEE2E2', '#B91C1C'),
                '띄어쓰기': ('#DCFCE7', '#15803D'),
                '표준어 의심': ('#E0E7FF', '#4338CA'),
                '통계적 교정': ('#F3E8FF', '#7E22CE')
            }
            for cat, count in counts.items():
                if count > 0:
                    bg, fg = colors.get(cat, ('#F1F5F9', '#475569'))
                    badge = QtWidgets.QLabel(f"{cat} {count}")
                    badge.setStyleSheet(f"""
                        background-color: {bg};
                        color: {fg};
                        font-size: 11px;
                        font-weight: 700;
                        padding: 2px 7px;
                        border-radius: 4px;
                    """)
                    self.badge_box.addWidget(badge)

            # Populate guide cards
            items = result.get('items', [])
            for idx, it in enumerate(items):
                card = self._create_guide_card(it)
                self.items_layout.insertWidget(idx, card)

    def _create_guide_card(self, it: dict) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        l = QtWidgets.QVBoxLayout(card)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(4)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)

        lbl_type = QtWidgets.QLabel(f"{it.get('icon', '✏️')} {it.get('type', '교정')}")
        lbl_type.setStyleSheet(f"""
            background-color: {it.get('badge_bg', '#F1F5F9')};
            color: {it.get('color', '#334155')};
            font-size: 11px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        top.addWidget(lbl_type)

        lbl_orig = QtWidgets.QLabel(it.get('original', ''))
        lbl_orig.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: 600; text-decoration: line-through;")
        top.addWidget(lbl_orig)

        lbl_arrow = QtWidgets.QLabel("➔")
        lbl_arrow.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        top.addWidget(lbl_arrow)

        lbl_corr = QtWidgets.QLabel(it.get('corrected', ''))
        lbl_corr.setStyleSheet("color: #10B981; font-size: 14px; font-weight: 700;")
        top.addWidget(lbl_corr)

        top.addStretch()
        l.addLayout(top)

        guide_text = it.get('guide', '')
        if guide_text:
            lbl_tip = QtWidgets.QLabel(f"💡 {guide_text}")
            lbl_tip.setWordWrap(True)
            lbl_tip.setStyleSheet("color: #475569; font-size: 12px; margin-top: 2px; line-height: 1.4;")
            l.addWidget(lbl_tip)

        return card

    def _on_replace_clicked(self):
        if not self.current_result:
            return
        self._on_copy_clicked()

    def _on_copy_clicked(self):
        if not self.current_result:
            return
        corrected = self.current_result.get('corrected', '')
        if TextManager.copy_to_clipboard(corrected):
            self.lbl_toast.setText("✓ 복사되었습니다!")
            self.lbl_toast.show()
            QtCore.QTimer.singleShot(2500, self.lbl_toast.hide)

    def _on_editor_clicked(self):
        if not self.current_result:
            return
        orig = self.current_result.get('original', '')
        corr = self.current_result.get('corrected', '')
        self.was_replaced = True
        self.hide()
        self.open_editor_requested.emit(orig, corr)

    def _on_close(self):
        if not self.was_replaced:
            TextManager.cancel_selection(self.target_hwnd, self.selection_mode)
        self.hide()

    def show_guidelines(self, result: dict, target_hwnd=None, selection_mode="selected", center_near_mouse=True):
        self.set_result(result, target_hwnd, selection_mode)
        if center_near_mouse:
            cursor_pos = QtGui.QCursor.pos()
            screen = QtGui.QGuiApplication.primaryScreen().geometry()
            x = cursor_pos.x() - (self.width() // 2)
            y = cursor_pos.y() - (self.height() // 2)

            # Keep in screen
            x = max(20, min(x, screen.width() - self.width() - 20))
            y = max(20, min(y, screen.height() - self.height() - 20))
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)
