# -*- coding: utf-8 -*-
"""Bounded Qt screen capture; actual OCR is run only by the isolated worker."""
from PyQt6 import QtGui, QtCore


class CursorTextRecognizer:
    def __init__(self, ocr_width=700, ocr_height=140):
        self.ocr_width = min(1400, max(100, int(ocr_width)))
        self.ocr_height = min(400, max(40, int(ocr_height)))

    def capture_png(self, x, y):
        point = QtCore.QPoint(x, y)
        screen = QtGui.QGuiApplication.screenAt(point)
        if screen is None:
            raise ValueError('마우스 위치의 모니터를 찾을 수 없습니다.')
        bounds = screen.geometry()
        area = QtCore.QRect(x - self.ocr_width // 2, y - self.ocr_height // 2,
                            self.ocr_width, self.ocr_height).intersected(bounds)
        pixmap = screen.grabWindow(0, area.x() - bounds.x(), area.y() - bounds.y(),
                                   area.width(), area.height())
        if pixmap.isNull():
            raise ValueError('화면을 캡처하지 못했습니다.')
        data = QtCore.QByteArray()
        buffer = QtCore.QBuffer(data)
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, 'PNG'):
            raise ValueError('화면 이미지 변환에 실패했습니다.')
        buffer.close()
        return bytes(data)

    async def _run_async_ocr(self, png_bytes):
        import winrt.windows.media.ocr as ocr
        import winrt.windows.globalization as glob
        import winrt.windows.graphics.imaging as imaging
        import winrt.windows.storage.streams as streams
        engine = ocr.OcrEngine.try_create_from_language(glob.Language('ko'))
        if not engine:
            engine = ocr.OcrEngine.try_create_from_user_profile_languages()
        if not engine:
            raise ValueError('Windows 한국어 OCR 언어팩이 필요합니다.')
        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream)
        try:
            writer.write_bytes(png_bytes)
            await writer.store_async()
            await writer.flush_async()
            writer.detach_stream()
            stream.seek(0)
            decoder = await imaging.BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            result = await engine.recognize_async(bitmap)
            return ' '.join(line.text.strip() for line in result.lines if line.text.strip())
        finally:
            writer.close()
            stream.close()
