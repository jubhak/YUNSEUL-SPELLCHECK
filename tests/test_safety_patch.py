"""Regression tests. Windows/UIA providers are simulated; real Windows QA required."""
import ast
import contextlib
import ctypes
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from app.sentence_scope import sentence_at, MAX_SENTENCE, CONTEXT_CHARS
from app.capture_worker import _range_sentence, capture_text, worker_main


class Range:
    """Minimal UIA range model; GetText(-1) deliberately forbidden."""
    def __init__(self, text, start, end=None, calls=None):
        self.text, self.start = text, start
        self.end = start if end is None else end
        self.calls = calls if calls is not None else []

    def Clone(self):
        return Range(self.text, self.start, self.end, self.calls)

    def MoveEndpointByRange(self, endpoint, other, target, waitTime=0):
        value = other.start if target == 0 else other.end
        if endpoint == 0:
            self.start = value
        else:
            self.end = value

    def MoveEndpointByUnit(self, endpoint, unit, count, waitTime=0):
        assert unit == 0
        if endpoint == 0:
            self.start = max(0, self.start + count)
        else:
            self.end = min(len(self.text), self.end + count)

    def GetText(self, limit):
        assert 0 < limit <= CONTEXT_CHARS + 1
        self.calls.append(limit)
        return self.text[self.start:self.end][:limit]


@pytest.mark.parametrize('text,position,expected', [
    ('첫 문장입니다. 다음 문장입니다.', 2, '첫 문장입니다.'),
    ('첫 문장입니다. 다음 문장입니다.', 13, '다음 문장입니다.'),
    ('첫 줄\n둘째 줄', 6, '둘째 줄'),
    ('첫 줄\r\n둘째 줄', 8, '둘째 줄'),
    ('문장 하나', 1000, '문장 하나'),
    ('문장 하나', -3, '문장 하나'),
    ('', 0, ''),
    ('정말요?! 다음입니다.', 2, '정말요?!'),
    ('그는 “맞아요.” 다음 글', 4, '그는 “맞아요.”'),
])
def test_sentence_boundaries(text, position, expected):
    assert sentence_at(text, position) == expected


def test_sentence_limit():
    assert sentence_at('가' * MAX_SENTENCE, 0)
    assert sentence_at('가' * (MAX_SENTENCE + 1), 0) == ''


def test_large_notepad_document_only_one_sentence():
    first = '앞에 있는 문장입니다.\n' * 100000
    target = '여기에 틀린 문장이 있어요.'
    doc = first + target + '\n' + '뒤에 있는 문장입니다.\n' * 100000
    rng = Range(doc, len(first) + 6)
    assert _range_sentence(rng) == target
    assert len(rng.calls) == 2
    assert max(rng.calls) == CONTEXT_CHARS + 1


def test_selected_multiple_sentences_still_checks_one():
    doc = '첫 문장입니다. 다음 문장입니다.'
    assert _range_sentence(Range(doc, 2, len(doc))) == '첫 문장입니다.'


def test_long_unbroken_line_fails_closed():
    assert _range_sentence(Range('가' * 100000, 50000)) == ''


def test_eof_caret():
    assert _range_sentence(Range('검사할 문장입니다.', 10)) == '검사할 문장입니다.'


def install_fake_uia(monkeypatch, value='한글 검색어', tp=None, password=False, foreign=False):
    class Fn:
        def __init__(self, func): self.func = func
        def __call__(self, *args): return self.func(*args)
    def thread_pid(hwnd, out):
        out._obj.value = 17
        return 23
    user32 = SimpleNamespace(
        GetWindowThreadProcessId=Fn(thread_pid),
        GetForegroundWindow=Fn(lambda: 42),
        PostMessageW=Fn(lambda *args: 1))
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *a, **k: user32, raising=False)
    elem = SimpleNamespace(ProcessId=18 if foreign else 17, IsPassword=password,
                           ControlType=1, GetRuntimeId=lambda: [3, 42],
                           GetParentControl=lambda: None)
    elem.GetPattern = lambda kind: tp if kind == 10 else SimpleNamespace(Value=value)
    auto = SimpleNamespace(UIAutomationInitializerInThread=contextlib.nullcontext,
                           SetGlobalSearchTimeout=lambda _: None,
                           ControlFromHandle=lambda _: elem,
                           GetFocusedControl=lambda: elem,
                           ControlFromPoint=lambda x, y: elem,
                           ControlType=SimpleNamespace(MenuControl=3, MenuItemControl=4, EditControl=1, ComboBoxControl=2),
                           PatternId=SimpleNamespace(TextPattern=10, ValuePattern=11))
    monkeypatch.setitem(sys.modules, 'uiautomation', auto)
    return elem


def capture_payload():
    return {'hwnd': 42, 'pid': 17, 'focus_hwnd': 43, 'x': 50, 'y': 70}


def test_search_field_valuepattern_uses_correct_property(monkeypatch):
    install_fake_uia(monkeypatch)
    result = capture_text(capture_payload())
    assert result['text'] == '한글 검색어'
    assert result['method'] == 'uia_value_single_sentence'


def test_explorer_address_valuepattern(monkeypatch):
    install_fake_uia(monkeypatch, value='C:\\사용자\\한글 폴더')
    assert capture_text(capture_payload())['text'] == 'C:\\사용자\\한글 폴더'


def test_rangefrompoint_two_arguments(monkeypatch):
    point = Mock(return_value=Range('한글 문장입니다.', 3))
    tp = SimpleNamespace(GetSelection=lambda: [], RangeFromPoint=point)
    install_fake_uia(monkeypatch, tp=tp)
    assert capture_text(capture_payload())['text'] == '한글 문장입니다.'
    point.assert_called_once_with(50, 70)


def test_broken_textpattern_falls_back_to_value(monkeypatch):
    tp = SimpleNamespace(GetSelection=Mock(side_effect=RuntimeError('unsupported')))
    install_fake_uia(monkeypatch, tp=tp)
    assert capture_text(capture_payload())['text'] == '한글 검색어'


@pytest.mark.parametrize('value,password,foreign', [
    ('비밀번호', True, False), ('다른 앱', False, True),
    ('첫 문장. 둘째 문장.', False, False), ('가' * 10001, False, False),
], ids=['pwd', 'foreign', 'two_sent', 'oversized'])
def test_reject_unsafe_value(monkeypatch, value, password, foreign):
    install_fake_uia(monkeypatch, value=value, password=password, foreign=foreign)
    assert capture_text(capture_payload())['text'] == ''


def test_window_pid_change(monkeypatch):
    install_fake_uia(monkeypatch)
    payload = capture_payload()
    payload['pid'] = 99
    assert '바뀌' in capture_text(payload)['error']


def test_chunk_lengths_and_source_preservation(monkeypatch):
    from app.checker import SpellCheckerEngine
    engine = SpellCheckerEngine()
    seen = []
    def check(text):
        seen.append(text)
        return {'corrected': text, 'items': [], 'err_count': 0, 'counts': {}}
    monkeypatch.setattr(engine, '_check_single', check)
    source = '가' * 1100 + '\n둘째 줄\n'
    result = engine._check_chunks(source)
    assert max(map(len, seen)) <= 450
    assert ''.join(seen) == source
    assert result['corrected'] == source


def test_oversized_clipboard_never_reaches_checker():
    connection = SimpleNamespace(send=Mock(), close=Mock())
    worker_main(connection, {'kind': 'clipboard', 'text': '가' * 4001})
    assert '4,000' in connection.send.call_args[0][0]['error']
    connection.close.assert_called_once()


def forever_worker(connection, payload):
    while True:
        time.sleep(1)


def test_watchdog_kills_stuck_provider_without_blocking_qt(monkeypatch):
    from PyQt6 import QtCore
    from app import safe_job
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    monkeypatch.setattr(safe_job, 'worker_main', forever_worker)
    job = safe_job.SafeJob()
    replies, ticks = [], []
    job.finished.connect(replies.append)
    heartbeat = QtCore.QTimer()
    heartbeat.setInterval(10)
    heartbeat.timeout.connect(lambda: ticks.append(1))
    heartbeat.start()
    try:
        assert job.start({'kind': 'auto'})
        assert not job.start({'kind': 'auto'})
        job._deadline = time.monotonic() + 0.4
        limit = time.monotonic() + 5
        while time.monotonic() < limit and (not replies or job.busy):
            app.processEvents()
            time.sleep(0.005)
        assert replies and '중단' in replies[0]['error']
        assert len(ticks) > 10
        assert not job.busy
    finally:
        heartbeat.stop()
        job.shutdown()


def test_no_input_injection_or_unbounded_text_reads():
    root = Path(__file__).resolve().parents[1]
    for name in ['app/text_manager.py', 'app/mouse_hook.py', 'app/capture_worker.py', 'app/app_controller.py']:
        source = (root/name).read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {'AttachThreadInput', 'keybd_event', 'SendInput'}
                if node.func.attr == 'GetText':
                    assert not any(isinstance(arg, ast.UnaryOp) for arg in node.args)


def test_freeze_support_precedes_app_start():
    source = (Path(__file__).resolve().parents[1]/'main.py').read_text(encoding='utf-8')
    assert source.index('multiprocessing.freeze_support()') < source.rindex('    main()')
