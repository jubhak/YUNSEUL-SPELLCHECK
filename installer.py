# -*- coding: utf-8 -*-
"""YUNSEUL-SPELLCHECK 설치 마법사 (tkinter). 빌드된 Setup.exe가 자기 자신을 복사해 설치합니다."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "YUNSEUL-SPELLCHECK"
EXE_NAME = "SPELLCHECK.exe"
INSTALL_DIR_DEFAULT = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", APP_NAME)

BG = "#0f172a"
CARD = "#1e293b"
LINE = "#334155"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
BTN = "#0284c7"
BTN_HOVER = "#0369a1"


def bundle_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def icon_path() -> str:
    ico = os.path.join(bundle_dir(), "app_icon.ico")
    if os.path.isfile(ico):
        return ico
    ico_assets = os.path.join(bundle_dir(), "assets", "icon.ico")
    if os.path.isfile(ico_assets):
        return ico_assets
    return ""


def apply_icon(win: tk.Misc) -> None:
    ico = icon_path()
    if ico:
        try:
            win.iconbitmap(ico)
        except tk.TclError:
            pass


def create_shortcut(target, shortcut_path, icon_path="", description=""):
    try:
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.WorkingDirectory = "{os.path.dirname(target)}";'
        )
        if icon_path and os.path.exists(icon_path):
            ps_cmd += f' $s.IconLocation = "{icon_path}";'
        if description:
            ps_cmd += f' $s.Description = "{description}";'
        ps_cmd += " $s.Save()"
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def install_files(target_dir: str, create_desktop: bool, create_startmenu: bool, progress_cb) -> str:
    progress_cb(10, "설치 디렉토리 생성 중...")
    os.makedirs(target_dir, exist_ok=True)

    progress_cb(40, "프로그램 파일 복사 중...")
    target_exe = os.path.join(target_dir, EXE_NAME)

    if getattr(sys, "frozen", False):
        shutil.copy2(sys.executable, target_exe)
    else:
        # Development fallback
        with open(target_exe, "w") as f:
            f.write("# Portable placeholder")

    progress_cb(75, "바로가기 생성 중...")
    desc = "윤슬 맞춤법 및 띄어쓰기 검사기"
    icon = target_exe

    if create_desktop:
        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        if os.path.isdir(desktop):
            create_shortcut(target_exe, os.path.join(desktop, f"{APP_NAME}.lnk"), icon, desc)

    if create_startmenu:
        startmenu = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            APP_NAME,
        )
        os.makedirs(startmenu, exist_ok=True)
        create_shortcut(target_exe, os.path.join(startmenu, f"{APP_NAME}.lnk"), icon, desc)

    progress_cb(100, "설치가 성공적으로 완료되었습니다.")
    return target_exe


class SetupWizard:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("YUNSEUL-SPELLCHECK 설치 마법사")
        self.root.geometry("620x540")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        apply_icon(self.root)

        self.page = 0
        self.installed_exe = ""
        self._install_started = False
        self._install_result: tuple[bool, str] | None = None
        self.target_dir_var = tk.StringVar(value=INSTALL_DIR_DEFAULT)
        self.desktop_var = tk.BooleanVar(value=True)
        self.startmenu_var = tk.BooleanVar(value=True)
        self.run_var = tk.BooleanVar(value=True)

        self._style_ttk()
        self._build()
        self._show_page(0)

    def _style_ttk(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Setup.Horizontal.TProgressbar",
            troughcolor=CARD,
            background="#0284c7",
            bordercolor=LINE,
            lightcolor="#0284c7",
            darkcolor="#0284c7",
        )

    def _build(self) -> None:
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=24, pady=(20, 8))

        self.pages = [
            self._page_intro(),
            self._page_dir(),
            self._page_progress(),
            self._page_finish(),
        ]
        for p in self.pages:
            p.place(in_=self.body, x=0, y=0, relwidth=1, relheight=1)

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=24, pady=(0, 18))
        self.btn_cancel = self._btn(bar, "취소", self._on_cancel, secondary=True)
        self.btn_cancel.pack(side="right")
        self.btn_next = self._btn(bar, "다음 >", self._on_next)
        self.btn_next.pack(side="right", padx=(0, 8))
        self.btn_back = self._btn(bar, "< 이전", self._on_back, secondary=True)
        self.btn_back.pack(side="right", padx=(0, 8))

    def _btn(self, parent, text, cmd, secondary=False) -> tk.Button:
        bg = CARD if secondary else BTN
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=TEXT,
            activebackground=BTN_HOVER if not secondary else LINE,
            activeforeground=TEXT,
            relief="flat",
            font=("Malgun Gothic", 10, "bold"),
            padx=16,
            pady=7,
            cursor="hand2",
            bd=0,
        )

    def _card(self, parent) -> tk.Frame:
        return tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=16, pady=12)

    def _title(self, parent, text: str) -> tk.Label:
        return tk.Label(parent, text=text, fg=ACCENT, bg=BG, font=("Malgun Gothic", 16, "bold"), anchor="w", justify="left")

    def _sub(self, parent, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            fg=MUTED,
            bg=BG,
            font=("Malgun Gothic", 10),
            anchor="w",
            justify="left",
            wraplength=550,
        )

    def _page_intro(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG)
        self._title(f, "윤슬 맞춤법 검사기 설치를 시작합니다").pack(anchor="w")
        self._sub(
            f,
            "웹 브라우저, 메모장 어디서든 마우스 우클릭으로 맞춤법을 검사하고 가이드라인을 확인하세요.\n"
            "시스템 Python 설치 없이 독립 실행되는 클린 프로그램입니다.",
        ).pack(anchor="w", pady=(8, 14))

        box = self._card(f)
        box.pack(fill="x")
        for line in (
            "주요 기능 안내:",
            "• 웹 브라우저, 메신저 등 어디서든 우클릭으로 [맞춤법 검사] 호출",
            "• 단축키 Alt + S 로 선택 영역 즉시 검사",
            "• 맞춤법 / 띄어쓰기 / 표준어 / 통계교정 가이드라인 팝업",
            "• [원문에 바로 적용] 원클릭 자동 치환",
            "• 단일 독립 실행 파일 — 별도 런타임 설치 불필요",
        ):
            tk.Label(box, text=line, fg=TEXT, bg=CARD, font=("Malgun Gothic", 9), anchor="w").pack(anchor="w", pady=1)

        notice = self._card(f)
        notice.pack(fill="x", pady=(12, 0))
        tk.Label(
            notice,
            text="클린 포터블 설치 & 간편 삭제 안내",
            fg=ACCENT,
            bg=CARD,
            font=("Malgun Gothic", 10, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            notice,
            text="윈도우 레지스트리를 오염시키지 않는 안전한 클린 설치 방식입니다.\n"
            "삭제를 원하실 경우 설치 경로의 폴더만 휴지통에 버리시면 완전히 삭제됩니다.",
            fg="#cbd5e1",
            bg=CARD,
            font=("Malgun Gothic", 9),
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 8))
        row = tk.Frame(notice, bg=CARD)
        row.pack(fill="x")
        tk.Label(row, text="기본 설치 경로:", fg=MUTED, bg=CARD, font=("Malgun Gothic", 8, "bold")).pack(side="left")
        path = tk.Entry(
            row,
            font=("Consolas", 9),
            bg=BG,
            fg=ACCENT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
        )
        path.insert(0, INSTALL_DIR_DEFAULT)
        path.configure(state="readonly")
        path.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=4)
        return f

    def _page_dir(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG)
        self._title(f, "설치 위치 및 옵션 선택").pack(anchor="w")
        self._sub(f, "프로그램을 설치할 폴더를 지정해 주세요:").pack(anchor="w", pady=(8, 10))

        row = tk.Frame(f, bg=BG)
        row.pack(fill="x")
        entry = tk.Entry(
            row,
            textvariable=self.target_dir_var,
            font=("Malgun Gothic", 10),
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=ACCENT,
        )
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self._btn(row, "찾아보기...", self._browse).pack(side="left")

        tk.Label(f, text="바로가기 아이콘 생성 옵션:", fg=ACCENT, bg=BG, font=("Malgun Gothic", 10, "bold")).pack(
            anchor="w", pady=(18, 8)
        )
        self._check(f, "바탕화면에 바로가기 아이콘 만들기", self.desktop_var)
        self._check(f, "시작 메뉴 프로그램 목록에 등록", self.startmenu_var)
        return f

    def _check(self, parent, text, var) -> None:
        tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            bg=BG,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=BG,
            activeforeground=TEXT,
            font=("Malgun Gothic", 10),
            anchor="w",
        ).pack(anchor="w", pady=3)

    def _page_progress(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG)
        self._title(f, "프로그램 설치 중").pack(anchor="w")
        self.status_lbl = self._sub(f, "설치 준비 중...")
        self.status_lbl.pack(anchor="w", pady=(10, 12))
        self.progress = ttk.Progressbar(f, style="Setup.Horizontal.TProgressbar", maximum=100, length=540)
        self.progress.pack(fill="x")
        return f

    def _page_finish(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG)
        self._title(f, "윤슬 맞춤법 검사기 설치가 완료되었습니다!").pack(anchor="w")
        self._sub(f, "바탕화면 또는 시작 메뉴의 바로가기로 프로그램을 즉시 실행할 수 있습니다.").pack(
            anchor="w", pady=(8, 14)
        )

        notice = self._card(f)
        notice.pack(fill="x")
        tk.Label(
            notice,
            text="프로그램 제거(삭제) 안내",
            fg=ACCENT,
            bg=CARD,
            font=("Malgun Gothic", 10, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            notice,
            text="윈도우 레지스트리를 전혀 사용하지 않는 완전한 클린 포터블 방식입니다.\n"
            "프로그램을 제거하려면 아래 폴더만 삭제하시면 됩니다:",
            fg="#cbd5e1",
            bg=CARD,
            font=("Malgun Gothic", 9),
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 8))
        row = tk.Frame(notice, bg=CARD)
        row.pack(fill="x")
        self.finish_path = tk.Entry(
            row,
            font=("Consolas", 9),
            bg=BG,
            fg=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.finish_path.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        self._btn(row, "폴더 열기", self._open_folder, secondary=True).pack(side="left")
        self._check(f, "지금 바로 윤슬 맞춤법 검사기 실행하기", self.run_var)
        return f

    def _browse(self) -> None:
        d = filedialog.askdirectory(title="설치 폴더 선택", initialdir=self.target_dir_var.get())
        if d:
            self.target_dir_var.set(os.path.join(d, APP_NAME))

    def _open_folder(self) -> None:
        path = self.target_dir_var.get().strip()
        if path and os.path.isdir(path):
            os.startfile(path)

    def _show_page(self, idx: int) -> None:
        self.page = idx
        for i, p in enumerate(self.pages):
            if i == idx:
                p.lift()
        self.btn_back.configure(state="disabled" if idx in (0, 2, 3) else "normal")
        if idx == 3:
            self.btn_next.configure(text="완료")
            self.btn_cancel.configure(state="disabled")
        else:
            self.btn_next.configure(text="다음 >")
            self.btn_cancel.configure(state="normal")
        if idx == 2:
            self.btn_next.configure(state="disabled")
            self._start_install()
        else:
            self.btn_next.configure(state="normal")

    def _on_back(self) -> None:
        if self.page == 1:
            self._show_page(0)

    def _on_next(self) -> None:
        if self.page == 0:
            self._show_page(1)
        elif self.page == 1:
            target = self.target_dir_var.get().strip()
            if not target:
                messagebox.showwarning("설치 위치", "설치 폴더를 입력해 주세요.")
                return
            self._show_page(2)
        elif self.page == 3:
            self._finish()

    def _on_cancel(self) -> None:
        self.root.destroy()

    def _start_install(self) -> None:
        if self._install_started:
            return
        self._install_started = True
        target = self.target_dir_var.get().strip()
        desktop = self.desktop_var.get()
        startmenu = self.startmenu_var.get()

        def work() -> None:
            try:
                exe = install_files(target, desktop, startmenu, self._set_progress)
                self._install_result = (True, exe)
            except Exception as exc:
                self._install_result = (False, str(exc))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(80, self._poll_install)

    def _set_progress(self, pct: int, msg: str) -> None:
        self.root.after(0, lambda: (self.progress.configure(value=pct), self.status_lbl.configure(text=msg)))

    def _poll_install(self) -> None:
        if self._install_result is None:
            self.root.after(80, self._poll_install)
            return
        ok, result = self._install_result
        if ok:
            self.installed_exe = result
            self.finish_path.configure(state="normal")
            self.finish_path.delete(0, "end")
            self.finish_path.insert(0, self.target_dir_var.get().strip())
            self.finish_path.configure(state="readonly")
            self._show_page(3)
        else:
            messagebox.showerror("설치 실패", f"설치 중 오류가 발생했습니다:\n{result}")
            self.root.destroy()

    def _finish(self) -> None:
        if self.run_var.get() and self.installed_exe and os.path.isfile(self.installed_exe):
            subprocess.Popen([self.installed_exe], cwd=os.path.dirname(self.installed_exe))
        self.root.destroy()

    def run(self) -> int:
        self.root.mainloop()
        return 0


def main() -> int:
    SetupWizard().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
