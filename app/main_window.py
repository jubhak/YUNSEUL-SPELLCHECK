from PyQt6 import QtWidgets, QtCore, QtGui
from app.checker import SpellCheckerEngine
from app.text_manager import TextManager

class MainWindow(QtWidgets.QMainWindow):
    settings_changed = QtCore.pyqtSignal(dict)

    def __init__(self, spell_engine: SpellCheckerEngine, config: dict):
        super().__init__()
        self.spell_engine = spell_engine
        self.config = config

        self.setWindowTitle("윤슬 맞춤법 & 띄어쓰기 검사기")
        self.resize(880, 680)
        self.setMinimumSize(750, 550)

        self._init_ui()

    def _init_ui(self):
        # Central widget with tabs
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tabs
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background: #FFFFFF;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #475569;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #0284C7;
                border-bottom: 2px solid #0284C7;
            }
        """)

        # Tab 1: Spell Check Editor
        self.tab_editor = QtWidgets.QWidget()
        self._init_editor_tab(self.tab_editor)
        self.tab_widget.addTab(self.tab_editor, "📝 맞춤법 검사기")

        # Tab 2: Settings
        self.tab_settings = QtWidgets.QWidget()
        self._init_settings_tab(self.tab_settings)
        self.tab_widget.addTab(self.tab_settings, "⚙️ 환경 설정")

        main_layout.addWidget(self.tab_widget)

    def _init_editor_tab(self, parent):
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Splitter: Left = Input, Right = Output
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Left: Original text panel
        panel_left = QtWidgets.QWidget()
        l_left = QtWidgets.QVBoxLayout(panel_left)
        l_left.setContentsMargins(0, 0, 0, 0)
        l_left.setSpacing(8)

        lbl_input = QtWidgets.QLabel("검사할 원본 문장")
        lbl_input.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")
        l_left.addWidget(lbl_input)

        self.edit_input = QtWidgets.QTextEdit()
        self.edit_input.setPlaceholderText("검사할 문장을 입력하거나 웹/문서에서 복사해 붙여넣으세요...\n예: 안녕하새요 반갑습니당 맞춤법검사를합시다 감기빨리 낳으세요")
        self.edit_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.5;
                font-family: 'Malgun Gothic', sans-serif;
            }
            QTextEdit:focus {
                border: 1.5px solid #38BDF8;
            }
        """)
        self.edit_input.textChanged.connect(self._on_input_text_changed)
        l_left.addWidget(self.edit_input)

        # Left bottom buttons
        bar_left = QtWidgets.QHBoxLayout()
        self.lbl_char_count = QtWidgets.QLabel("0 글자")
        self.lbl_char_count.setStyleSheet("color: #94A3B8; font-size: 12px;")
        bar_left.addWidget(self.lbl_char_count)
        bar_left.addStretch()

        btn_paste = QtWidgets.QPushButton("붙여넣기")
        btn_paste.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 10px; font-size: 12px;")
        btn_paste.clicked.connect(self.edit_input.paste)
        bar_left.addWidget(btn_paste)

        btn_clear = QtWidgets.QPushButton("지우기")
        btn_clear.setStyleSheet("background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 10px; font-size: 12px;")
        btn_clear.clicked.connect(self.edit_input.clear)
        bar_left.addWidget(btn_clear)

        btn_check = QtWidgets.QPushButton("🚀 맞춤법 검사")
        btn_check.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_check.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_check.clicked.connect(self._run_spell_check)
        bar_left.addWidget(btn_check)

        l_left.addLayout(bar_left)
        splitter.addWidget(panel_left)

        # Right: Corrected text & guidelines
        panel_right = QtWidgets.QWidget()
        l_right = QtWidgets.QVBoxLayout(panel_right)
        l_right.setContentsMargins(0, 0, 0, 0)
        l_right.setSpacing(8)

        lbl_result = QtWidgets.QLabel("교정 결과 및 가이드라인")
        lbl_result.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")
        l_right.addWidget(lbl_result)

        self.edit_output = QtWidgets.QTextEdit()
        self.edit_output.setReadOnly(True)
        self.edit_output.setStyleSheet("""
            QTextEdit {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.5;
                font-family: 'Malgun Gothic', sans-serif;
            }
        """)
        l_right.addWidget(self.edit_output)

        # Right bottom buttons
        bar_right = QtWidgets.QHBoxLayout()
        self.lbl_result_status = QtWidgets.QLabel("대기 중")
        self.lbl_result_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        bar_right.addWidget(self.lbl_result_status)
        bar_right.addStretch()

        self.btn_copy_output = QtWidgets.QPushButton("📋 교정문 복사")
        self.btn_copy_output.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_copy_output.clicked.connect(self._on_copy_result)
        bar_right.addWidget(self.btn_copy_output)

        l_right.addLayout(bar_right)
        splitter.addWidget(panel_right)

        layout.addWidget(splitter, stretch=1)

    def _init_settings_tab(self, parent):
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        grp_general = QtWidgets.QGroupBox("마우스 및 단축키 동작 설정")
        grp_general.setStyleSheet("QGroupBox { font-size: 14px; font-weight: 700; color: #1E293B; }")
        l_grp = QtWidgets.QVBoxLayout(grp_general)
        l_grp.setSpacing(12)
        l_grp.setContentsMargins(16, 20, 16, 16)

        # Checkbox: Right-click trigger
        self.chk_right_click = QtWidgets.QCheckBox("웹이나 모든 창에서 마우스 우클릭 시 '맞춤법 검사' 메뉴 띄우기 (추천)")
        self.chk_right_click.setChecked(self.config.get('enable_right_click', True))
        self.chk_right_click.setStyleSheet("font-size: 13px; color: #334155;")
        self.chk_right_click.stateChanged.connect(self._on_setting_changed)
        l_grp.addWidget(self.chk_right_click)

        # Checkbox: Drag selection trigger
        self.chk_drag_select = QtWidgets.QCheckBox("마우스로 텍스트 드래그(선택) 시 퀵 아이콘 띄우기")
        self.chk_drag_select.setChecked(self.config.get('enable_drag_select', True))
        self.chk_drag_select.setStyleSheet("font-size: 13px; color: #334155;")
        self.chk_drag_select.stateChanged.connect(self._on_setting_changed)
        l_grp.addWidget(self.chk_drag_select)

        # Checkbox: Close to tray
        self.chk_close_to_tray = QtWidgets.QCheckBox("창을 닫을 때 프로그램을 종료하지 않고 트레이로 최소화하기")
        self.chk_close_to_tray.setChecked(self.config.get('close_to_tray', True))
        self.chk_close_to_tray.setStyleSheet("font-size: 13px; color: #334155;")
        self.chk_close_to_tray.stateChanged.connect(self._on_setting_changed)
        l_grp.addWidget(self.chk_close_to_tray)

        layout.addWidget(grp_general)

        # Group: Cursor Recognition & OCR
        grp_ocr = QtWidgets.QGroupBox("마우스 커서 인식 및 화면 OCR 설정")
        grp_ocr.setStyleSheet("QGroupBox { font-size: 14px; font-weight: 700; color: #1E293B; }")
        l_ocr = QtWidgets.QVBoxLayout(grp_ocr)
        l_ocr.setSpacing(10)
        l_ocr.setContentsMargins(16, 20, 16, 16)

        row_w = QtWidgets.QHBoxLayout()
        lbl_w = QtWidgets.QLabel("화면 광학 문자 인식(OCR) 가로 스캔 너비:")
        lbl_w.setStyleSheet("font-size: 13px; color: #334155;")
        row_w.addWidget(lbl_w)

        self.spin_ocr_width = QtWidgets.QSpinBox()
        self.spin_ocr_width.setRange(300, 1600)
        self.spin_ocr_width.setSingleStep(50)
        self.spin_ocr_width.setValue(self.config.get('ocr_width', 700))
        self.spin_ocr_width.setSuffix(" px")
        self.spin_ocr_width.setStyleSheet("font-size: 13px; padding: 4px 8px; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.spin_ocr_width.valueChanged.connect(self._on_setting_changed)
        row_w.addWidget(self.spin_ocr_width)
        row_w.addStretch()
        l_ocr.addLayout(row_w)

        lbl_desc = QtWidgets.QLabel(
            "• 1. UI Automation: 마우스 커서가 가리키는 웹/문서 단어/문장 즉시 추출\n"
            "• 2. 700px 화면 OCR: 복사 금지 웹, PDF, 이미지 위 글자를 광학 인식\n"
            "• 3. 활성 입력창 캐럿: 글을 타이핑하던 중 우클릭 시 현재 작성 글 자동 추출"
        )
        lbl_desc.setStyleSheet("color: #64748B; font-size: 12px; line-height: 1.5;")
        l_ocr.addWidget(lbl_desc)

        layout.addWidget(grp_ocr)

        # Guide Box
        guide_box = QtWidgets.QFrame()
        guide_box.setStyleSheet("""
            QFrame {
                background: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        l_box = QtWidgets.QVBoxLayout(guide_box)
        lbl_info_title = QtWidgets.QLabel("💡 사용 가이드")
        lbl_info_title.setStyleSheet("font-weight: 700; color: #0369A1; font-size: 13px;")
        l_box.addWidget(lbl_info_title)

        lbl_info_desc = QtWidgets.QLabel(
            "1. 웹 브라우저(크롬, 엣지), 메모장, 카카오톡 등 어디서든 텍스트를 드래그하거나 작성 중 마우스 우클릭을 누르면 커서 위치에 [📝 맞춤법 검사] 메뉴가 나타납니다.\n"
            "2. 메뉴를 클릭하면 오타 및 띄어쓰기를 실시간 분석하여 친절한 가이드라인 팝업을 표시합니다.\n"
            "3. [⚡ 원문에 바로 적용] 버튼을 누르면 작업 중이던 창의 오타가 올바른 문장으로 즉시 자동 치환됩니다.\n"
            "4. 전역 단축키 Alt + S 로도 언제든지 즉시 검사할 수 있습니다."
        )
        lbl_info_desc.setWordWrap(True)
        lbl_info_desc.setStyleSheet("color: #0C4A6E; font-size: 12px; line-height: 1.6;")
        l_box.addWidget(lbl_info_desc)

        layout.addWidget(guide_box)
        layout.addStretch()

    def _on_input_text_changed(self):
        text = self.edit_input.toPlainText()
        self.lbl_char_count.setText(f"{len(text)} 글자")

    def _run_spell_check(self):
        text = self.edit_input.toPlainText().strip()
        if not text:
            QtWidgets.QMessageBox.information(self, "알림", "검사할 문장을 입력해 주세요.")
            return

        self.lbl_result_status.setText("검사 중...")
        QtWidgets.QApplication.processEvents()

        res = self.spell_engine.check(text)
        corrected = res.get('corrected', '')
        err_count = res.get('err_count', 0)

        # Format output with guidelines
        html = [f"<div style='font-size:14px; font-weight:bold; color:#1E293B; margin-bottom:8px;'>교정문:</div>"]
        html.append(f"<div style='background:#F0FDF4; border:1px solid #86EFAC; padding:10px; border-radius:6px; color:#166534; font-size:13px; margin-bottom:14px;'>{corrected}</div>")

        if err_count > 0:
            self.lbl_result_status.setText(f"⚠️ {err_count}개 교정 발견")
            self.lbl_result_status.setStyleSheet("color: #DC2626; font-weight: bold;")

            html.append("<div style='font-size:13px; font-weight:bold; color:#334155; margin-bottom:6px;'>상세 교정 내역:</div>")
            for it in res.get('items', []):
                t_color = it.get('color', '#334155')
                t_name = it.get('type', '교정')
                orig = it.get('original', '')
                corr = it.get('corrected', '')
                guide = it.get('guide', '')

                card = f"""
                <div style='background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px; margin-bottom:6px;'>
                    <span style='color:{t_color}; font-weight:bold;'>[{t_name}]</span>
                    <span style='color:#EF4444; text-decoration:line-through; margin-left:6px;'>{orig}</span>
                    <span style='color:#94A3B8;'>➔</span>
                    <span style='color:#10B981; font-weight:bold;'>{corr}</span>
                    <div style='color:#64748B; font-size:12px; margin-top:4px;'>💡 {guide}</div>
                </div>
                """
                html.append(card)
        else:
            self.lbl_result_status.setText("🎉 오류 없음 (완벽)")
            self.lbl_result_status.setStyleSheet("color: #059669; font-weight: bold;")
            html.append("<div style='color:#059669; font-weight:bold;'>축하합니다! 맞춤법과 띄어쓰기 오류가 없습니다.</div>")

        self.edit_output.setHtml("".join(html))

    def _on_copy_result(self):
        text = self.edit_input.toPlainText()
        if not text:
            return
        res = self.spell_engine.check(text)
        corr = res.get('corrected', '')
        if corr:
            TextManager.copy_to_clipboard(corr)
            self.btn_copy_output.setText("✓ 복사 완료!")
            QtCore.QTimer.singleShot(2000, lambda: self.btn_copy_output.setText("📋 교정문 복사"))

    def _on_setting_changed(self):
        self.config['enable_right_click'] = self.chk_right_click.isChecked()
        self.config['enable_drag_select'] = self.chk_drag_select.isChecked()
        self.config['close_to_tray'] = self.chk_close_to_tray.isChecked()
        if hasattr(self, 'spin_ocr_width'):
            self.config['ocr_width'] = self.spin_ocr_width.value()
        self.settings_changed.emit(self.config)

    def load_text(self, original_text: str, corrected_text: str = ""):
        self.tab_widget.setCurrentIndex(0)
        self.edit_input.setPlainText(original_text)
        if corrected_text:
            self._run_spell_check()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.config.get('close_to_tray', True):
            event.ignore()
            self.hide()
        else:
            event.accept()
