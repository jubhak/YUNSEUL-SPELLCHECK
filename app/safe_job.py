"""Qt watchdog for one isolated job; never wait synchronously for a provider."""
import multiprocessing as mp
import time
from PyQt6 import QtCore
from app.capture_worker import worker_main


class SafeJob(QtCore.QObject):
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._pipe = None
        self._retired = []
        self._deadline = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @property
    def busy(self):
        return self._process is not None or any(p.is_alive() for p in self._retired)

    def start(self, payload):
        if self.busy:
            return False
        ctx = mp.get_context('spawn')
        parent, child = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=worker_main, args=(child, payload), daemon=True)
        try:
            proc.start()
        except Exception:
            parent.close()
            child.close()
            raise
        child.close()
        self._process, self._pipe = proc, parent
        self._deadline = time.monotonic() + 8.0  # Includes frozen-exe startup.
        return True

    def _finish(self, reply):
        self._retire()
        self.finished.emit(reply)

    def _retire(self):
        if self._pipe:
            self._pipe.close()
            self._pipe = None
        if self._process:
            if self._process.is_alive():
                self._process.terminate()
            self._retired.append(self._process)
            self._process = None

    def _poll(self):
        for proc in self._retired[:]:
            if not proc.is_alive():
                proc.join(timeout=0)
                proc.close()
                self._retired.remove(proc)
        if self._process is None:
            return
        try:
            # At most two messages per tick; no unbounded drain loop.
            for _ in range(2):
                if not self._pipe.poll():
                    break
                reply = self._pipe.recv()
                if reply.get('phase') == 'checking':
                    self._deadline = time.monotonic() + 20.0
                else:
                    self._finish(reply)
                    return
            if time.monotonic() >= self._deadline:
                self._finish({'error': '외부 앱 또는 검사 서버 응답이 늦어 작업을 중단했습니다. 전체 선택이나 키 입력은 전송하지 않았습니다.'})
            elif not self._process.is_alive():
                self._finish({'error': '검사 작업이 비정상 종료되었습니다. 다시 시도해 주세요.'})
        except (EOFError, OSError):
            self._finish({'error': '검사 작업과의 연결이 종료되었습니다.'})

    def shutdown(self):
        self._timer.stop()
        self._retire()
        for proc in self._retired:
            if proc.is_alive():
                proc.terminate()
            else:
                proc.join(timeout=0)
                proc.close()
        self._retired.clear()
