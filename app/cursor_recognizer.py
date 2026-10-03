# -*- coding: utf-8 -*-
"""
마우스 커서 근처 텍스트 인식 엔진 (3대 인식 방식 통합)
1. 윈도우 UI Automation (RangeFromPoint) - 커서가 가리키는 특정 단어/문장 즉시 추출
2. 윈도우 네이티브 한국어 OCR (Windows.Media.Ocr) - 커서 중심 700px 화면 광학 문자 인식
3. 활성 입력창 캐럿(Caret) 텍스트 자동 추출 - 작성 중이던 문장 추출
"""

import sys
import asyncio
from PyQt6 import QtGui, QtCore

# UI Automation
try:
    import uiautomation as auto
except ImportError:
    auto = None

# Windows Native OCR
try:
    import winrt.windows.media.ocr as ocr
    import winrt.windows.globalization as glob
    import winrt.windows.graphics.imaging as imaging
    import winrt.windows.storage.streams as streams
    HAS_WINRT_OCR = True
except ImportError:
    HAS_WINRT_OCR = False

from app.text_manager import TextManager


class CursorTextRecognizer:
    def __init__(self, ocr_width: int = 700, ocr_height: int = 140):
        self.ocr_width = ocr_width
        self.ocr_height = ocr_height
        self._ocr_engine = None

    def _get_ocr_engine(self):
        if not HAS_WINRT_OCR:
            return None
        if self._ocr_engine is None:
            try:
                lang = glob.Language("ko")
                self._ocr_engine = ocr.OcrEngine.try_create_from_language(lang)
                if not self._ocr_engine:
                    self._ocr_engine = ocr.OcrEngine.try_create_from_user_profile_languages()
            except Exception as e:
                print(f"[OCR] Engine init error: {e}")
        return self._ocr_engine

    # -------------------------------------------------------------
    # 방식 1: 윈도우 UI Automation (RangeFromPoint)
    # -------------------------------------------------------------
    def get_text_via_ui_automation(self, x: int, y: int) -> dict:
        """
        마우스 좌표 (x, y)에 위치한 컨트롤에서 TextPattern을 통해
        커서 바로 아래의 단어(Word) 또는 문장(Line)을 직접 읽어옵니다.
        """
        if not auto:
            return {'success': False, 'text': '', 'method': 'uia'}

        try:
            elem = auto.ControlFromPoint(x, y)
            if not elem:
                return {'success': False, 'text': '', 'method': 'uia'}

            # 1. Try TextPattern RangeFromPoint
            try:
                tp = elem.GetPattern(auto.PatternId.TextPattern)
                if tp:
                    pt = auto.tagPOINT(x, y)
                    text_range = tp.RangeFromPoint(pt)
                    if text_range:
                        # First try word
                        text_range.ExpandToEnclosingUnit(auto.TextUnit.Word)
                        word = text_range.GetText(-1).strip()

                        # Then line for full sentence context
                        text_range.ExpandToEnclosingUnit(auto.TextUnit.Line)
                        line = text_range.GetText(-1).strip()

                        target = line if line else word
                        if target:
                            return {
                                'success': True,
                                'text': target,
                                'word': word,
                                'line': line,
                                'method': 'uia_text_pattern'
                            }
            except Exception:
                pass

            # 2. Try ValuePattern (for input fields)
            try:
                vp = elem.GetPattern(auto.PatternId.ValuePattern)
                if vp and vp.CurrentValue:
                    val = vp.CurrentValue.strip()
                    if val:
                        return {
                            'success': True,
                            'text': val,
                            'method': 'uia_value_pattern'
                        }
            except Exception:
                pass

            # 3. Try Name attribute
            name = elem.Name.strip() if elem.Name else ""
            if name and len(name) > 1 and not name.startswith("스크린"):
                return {
                    'success': True,
                    'text': name,
                    'method': 'uia_name'
                }

        except Exception as e:
            print(f"[UIA] Error at ({x}, {y}): {e}")

        return {'success': False, 'text': '', 'method': 'uia'}

    # -------------------------------------------------------------
    # 방식 2: 윈도우 내장 네이티브 OCR (700px 화면 인식)
    # -------------------------------------------------------------
    def get_text_via_ocr(self, x: int, y: int, width: int = None, height: int = None) -> dict:
        """
        마우스 좌표 (x, y)를 중심으로 700px 가로 영역을 캡처하여
        Windows.Media.Ocr 엔진으로 한국어 글자를 광학 인식합니다.
        """
        if not HAS_WINRT_OCR:
            return {'success': False, 'text': '', 'method': 'ocr', 'error': 'WinRT OCR not available'}

        w = width or self.ocr_width
        h = height or self.ocr_height

        screen = QtGui.QGuiApplication.primaryScreen()
        if not screen:
            return {'success': False, 'text': '', 'method': 'ocr'}

        # Calculate bounding box centered around (x, y)
        left = max(0, x - (w // 2))
        top = max(0, y - (h // 2))

        # Grab screen area
        pixmap = screen.grabWindow(0, left, top, w, h)
        if pixmap.isNull():
            return {'success': False, 'text': '', 'method': 'ocr'}

        # Save to PNG in memory
        byte_array = QtCore.QByteArray()
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buf, "PNG")
        png_bytes = bytes(byte_array)

        # Run async OCR
        try:
            recognized_text = asyncio.run(self._run_async_ocr(png_bytes))
            recognized_text = recognized_text.strip()
            if recognized_text:
                return {
                    'success': True,
                    'text': recognized_text,
                    'method': 'ocr_700px',
                    'bbox': (left, top, w, h)
                }
        except Exception as e:
            print(f"[OCR] Execution error: {e}")

        return {'success': False, 'text': '', 'method': 'ocr'}

    async def _run_async_ocr(self, png_bytes: bytes) -> str:
        engine = self._get_ocr_engine()
        if not engine:
            return ""

        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream)
        writer.write_bytes(png_bytes)
        await writer.store_async()
        await writer.flush_async()
        writer.detach_stream()
        stream.seek(0)

        decoder = await imaging.BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()

        result = await engine.recognize_async(bitmap)
        lines = [line.text.strip() for line in result.lines if line.text.strip()]
        return " ".join(lines)

    # -------------------------------------------------------------
    # 방식 3: 활성 입력창 캐럿 텍스트 자동 추출
    # -------------------------------------------------------------
    def get_text_via_input_caret(self, target_hwnd=None) -> dict:
        text, hwnd, mode = TextManager.get_text_from_active_input(target_hwnd, timeout=0.3)
        if text:
            return {
                'success': True,
                'text': text,
                'target_hwnd': hwnd,
                'selection_mode': mode,
                'method': 'caret_input'
            }
        return {'success': False, 'text': '', 'method': 'caret_input'}

    # -------------------------------------------------------------
    # 스마트 하이브리드 자동 감지 (우선순위 체인)
    # -------------------------------------------------------------
    def smart_detect(self, x: int, y: int, target_hwnd=None, forced_mode: str = None) -> dict:
        """
        우선순위에 따라 마우스 근처의 텍스트를 감지합니다:
        1. 이미 선택된 텍스트가 있으면 최우선
        2. 활성 입력창에서 작성 중이던 글 (방식 3)
        3. UI Automation RangeFromPoint로 커서 아래 단어/문장 (방식 1)
        4. 커서 중심 700px 화면 광학 문자 인식 OCR (방식 2)
        """
        if forced_mode == "ocr":
            return self.get_text_via_ocr(x, y)
        elif forced_mode == "uia":
            return self.get_text_via_ui_automation(x, y)
        elif forced_mode == "input":
            return self.get_text_via_input_caret(target_hwnd)

        # 1. Try input caret / existing selection first (fastest and most accurate for typing)
        res_input = self.get_text_via_input_caret(target_hwnd)
        if res_input['success'] and res_input['text']:
            return res_input

        # 2. Try UI Automation RangeFromPoint
        res_uia = self.get_text_via_ui_automation(x, y)
        if res_uia['success'] and res_uia['text']:
            return res_uia

        # 3. Fallback to 700px Screen OCR
        res_ocr = self.get_text_via_ocr(x, y)
        if res_ocr['success'] and res_ocr['text']:
            return res_ocr

        return {'success': False, 'text': '', 'method': 'none'}
