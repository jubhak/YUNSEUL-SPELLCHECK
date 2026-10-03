# -*- coding: utf-8 -*-
"""
YUNSEUL-SPELLCHECK 빌드 도구
앱 아이콘 생성 및 단일 PyInstaller 실행 파일 (Setup.exe 및 Portable .exe) 빌드
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_PNG = ROOT / "app_icon.png"
ICON_ICO = ROOT / "app_icon.ico"


def make_icon() -> None:
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import (
        QBrush,
        QColor,
        QGuiApplication,
        QImage,
        QLinearGradient,
        QPainter,
        QPen,
    )

    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv)

    size = 256
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. Background gradient rounded rectangle
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#0f172a"))
    grad.setColorAt(1.0, QColor("#0369a1"))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor("#38bdf8"), 4))
    p.drawRoundedRect(QRectF(10, 10, size - 20, size - 20), 48, 48)

    # 2. Document/text card background
    p.setBrush(QColor(255, 255, 255, 235))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(44, 44, 168, 168), 24, 24)

    # 3. Horizontal text lines simulation
    p.setPen(QPen(QColor("#94a3b8"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(70, 80), QPointF(150, 80))
    p.drawLine(QPointF(70, 110), QPointF(186, 110))
    p.drawLine(QPointF(70, 140), QPointF(130, 140))

    # 4. Big vibrant green checkmark
    p.setPen(QPen(QColor("#10b981"), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    points = [QPointF(110, 160), QPointF(138, 188), QPointF(196, 126)]
    for i in range(len(points) - 1):
        p.drawLine(points[i], points[i + 1])

    p.end()
    img.save(str(ICON_PNG))

    # Also save to assets
    os.makedirs(ROOT / "assets", exist_ok=True)
    img.save(str(ROOT / "assets" / "icon.png"))

    # Convert PNG to ICO format (Standard Windows ICO structure)
    png = ICON_PNG.read_bytes()
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 6 + 16)
    ICON_ICO.write_bytes(header + entry + png)
    (ROOT / "assets" / "icon.ico").write_bytes(header + entry + png)

    print(f"아이콘 생성 완료: {ICON_ICO}")


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise SystemExit(f"명령 실패: {cmd[0]} (code {res.returncode})")


def build() -> None:
    os.environ.pop("PYTHONHOME", None)
    os.environ.pop("PYTHONPATH", None)

    print("== 1. 아이콘 생성 ==")
    make_icon()

    print("== 2. PyInstaller 단일 실행 파일 빌드 ==")
    sep = ";" if os.name == "nt" else ":"
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile", "--windowed",
        "--name", "YUNSEUL-SPELLCHECK-Setup",
        "--icon", str(ICON_ICO),
        "--add-data", f"{ICON_ICO}{sep}.",
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--hidden-import", "installer",
        "--hidden-import", "pynput",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "uiautomation",
        "--hidden-import", "winrt",
        "--hidden-import", "winrt.windows.media.ocr",
        "--hidden-import", "winrt.windows.globalization",
        "--hidden-import", "winrt.windows.graphics.imaging",
        "--hidden-import", "winrt.windows.storage.streams",
        "--hidden-import", "winrt.windows.foundation",
        "--collect-submodules", "app",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide6",
        "--exclude-module", "PySide2",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "torch",
        "--exclude-module", "cv2",
        "--distpath", str(ROOT),
        "--workpath", str(ROOT / "dist" / "build_setup"),
        "--specpath", str(ROOT / "dist"),
        str(ROOT / "main.py"),
    ])

    setup_exe = ROOT / "YUNSEUL-SPELLCHECK-Setup.exe"
    portable_exe = ROOT / "YUNSEUL-SPELLCHECK.exe"

    if setup_exe.exists():
        print(f"== 3. 설치 마법사 빌드 완료: {setup_exe.name} (크기: {setup_exe.stat().st_size:,} 바이트) ==")
        # Also create the direct portable version
        shutil.copy2(setup_exe, portable_exe)
        print(f"== 4. 포터블 직접 실행 파일 생성 완료: {portable_exe.name} (크기: {portable_exe.stat().st_size:,} 바이트) ==")
    else:
        print("빌드 파일 생성 실패!")


if __name__ == "__main__":
    os.chdir(ROOT)
    build()
