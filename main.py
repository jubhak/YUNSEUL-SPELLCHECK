# -*- coding: utf-8 -*-
import sys
import os
import ctypes
from pathlib import Path

def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))

def app_dir() -> Path:
    if _frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def bundle_dir() -> Path:
    if _frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent

def is_setup_mode() -> bool:
    args = {a.lower() for a in sys.argv[1:]}
    if "--app" in args:
        return False
    if "--install" in args or "--setup" in args:
        return True
    name = Path(sys.executable if _frozen() else sys.argv[0]).stem.lower()
    return "setup" in name

def check_single_instance():
    """중복 실행 방지 (Windows Named Mutex)"""
    kernel32 = ctypes.windll.kernel32
    mutex_name = "Local\\YUNSEUL_SPELLCHECK_SINGLETON_MUTEX"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_err = kernel32.GetLastError()
    if last_err == 183:  # ERROR_ALREADY_EXISTS
        return None, False
    return mutex, True

def run_app():
    # 중복 실행 방지
    mutex, is_single = check_single_instance()
    if not is_single:
        # 이미 실행 중이면 조용히 종료 (중복 실행 방지)
        sys.exit(0)

    from PyQt6 import QtWidgets, QtCore, QtGui

    # Ensure high DPI scaling
    if hasattr(QtCore.Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    from app.app_controller import AppController

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set default system font
    font = QtGui.QFont("Malgun Gothic", 10)
    app.setFont(font)

    controller = AppController(app)
    controller.start()

    sys.exit(app.exec())

def main():
    if is_setup_mode():
        from installer import main as install_main
        sys.exit(install_main())
    else:
        run_app()

if __name__ == "__main__":
    # Must run before setup-mode detection, mutex creation or QApplication.
    # Frozen multiprocessing workers otherwise reopen the installer/application.
    import multiprocessing
    multiprocessing.freeze_support()
    main()
