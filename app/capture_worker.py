"""Killable UIA/network worker. Never send keystrokes or attach input queues."""
from app.sentence_scope import sentence_at, CONTEXT_CHARS, MAX_SENTENCE, MAX_VALUE


def _range_sentence(rng):
    # Collapse to the selection's active start, then read a fixed-size context.
    anchor = rng.Clone()
    anchor.MoveEndpointByRange(1, anchor, 0, waitTime=0)
    left = anchor.Clone()
    left.MoveEndpointByUnit(0, 0, -CONTEXT_CHARS, waitTime=0)
    prefix = left.GetText(CONTEXT_CHARS + 1)
    right = anchor.Clone()
    right.MoveEndpointByUnit(1, 0, CONTEXT_CHARS, waitTime=0)
    suffix = right.GetText(CONTEXT_CHARS + 1)
    # A missing boundary at a truncated edge is unsafe: never check half a sentence.
    context = prefix + suffix
    value = sentence_at(context, len(prefix))
    if not value:
        return ''
    if len(prefix) >= CONTEXT_CHARS and context.lstrip().startswith(value):
        return ''
    if len(suffix) >= CONTEXT_CHARS and context.rstrip().endswith(value):
        return ''
    return value


def capture_text(payload):
    import uiautomation as auto
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    hwnd = payload.get('hwnd')
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value or pid.value != payload.get('pid'):
        return {'text': '', 'error': '대상 창이 닫혔거나 바뀌었습니다.'}
    # Reject a stale request rather than inspect another application.
    if user32.GetForegroundWindow() != hwnd:
        return {'text': '', 'error': '대상 창의 포커스가 바뀌었습니다. 다시 우클릭해 주세요.'}
    # Cancel the native context menu asynchronously; no Escape/Alt injection.
    user32.PostMessageW(hwnd, 0x001F, 0, 0)  # WM_CANCELMODE
    import time
    time.sleep(0.08)
    x, y = payload['x'], payload['y']
    with auto.UIAutomationInitializerInThread():
        auto.SetGlobalSearchTimeout(0.25)
        candidates = []
        focus_hwnd = payload.get('focus_hwnd')
        if focus_hwnd and focus_hwnd != hwnd:
            try:
                candidates.append(auto.ControlFromHandle(focus_hwnd))
            except Exception:
                pass
        try:
            candidates.append(auto.GetFocusedControl())
        except Exception:
            pass
        try:
            candidates.append(auto.ControlFromPoint(x, y))
        except Exception:
            pass
        seen = set()
        for first in candidates:
            elem = first
            for _ in range(6):
                if not elem:
                    break
                try:
                    if elem.ProcessId != pid.value or elem.IsPassword:
                        break
                    key = tuple(elem.GetRuntimeId())
                    if key in seen:
                        break
                    seen.add(key)
                    # Do not accept menu labels, window titles or accessible Names as text.
                    kind = elem.ControlType
                    if kind in (auto.ControlType.MenuControl, auto.ControlType.MenuItemControl):
                        break
                    try:
                        tp = elem.GetPattern(auto.PatternId.TextPattern)
                        if tp:
                            ranges = tp.GetSelection()
                            anchor = ranges[0] if ranges else None
                            # Empty selection normally identifies the real insertion caret.
                            # If provider has no selection support, use original click coordinates.
                            if anchor is None:
                                anchor = tp.RangeFromPoint(x, y)
                            if anchor is not None:
                                text = _range_sentence(anchor)
                                if text:
                                    return {'text': text, 'method': 'uia_sentence', 'selection_mode': 'none'}
                    except Exception:
                        pass
                    # Single-line Edit/ComboBox often expose only ValuePattern
                    # (Chromium search fields and Explorer address controls).
                    # Do not guess a caret for multi-sentence values.
                    if kind in (auto.ControlType.EditControl, auto.ControlType.ComboBoxControl):
                        vp = elem.GetPattern(auto.PatternId.ValuePattern)
                        if vp:
                            value = vp.Value or ''
                            if 0 < len(value) <= MAX_VALUE:
                                text = sentence_at(value, 0)
                                if text and text == value.strip():
                                    return {'text': text, 'method': 'uia_value_single_sentence', 'selection_mode': 'none'}
                except Exception:
                    pass
                try:
                    elem = elem.GetParentControl()
                except Exception:
                    break
    return {'text': '', 'error': '입력 위치의 한 문장을 안전하게 읽지 못했습니다. 입력창을 클릭한 뒤 다시 시도하거나 복사 후 클립보드 검사를 사용해 주세요. (한 문장 최대 1,000자)'}


def worker_main(connection, payload):
    """Spawn entry point; send only small results over the pipe."""
    try:
        kind = payload.get('kind', 'auto')
        if kind == 'ocr':
            import asyncio
            from app.cursor_recognizer import CursorTextRecognizer
            text = asyncio.run(CursorTextRecognizer()._run_async_ocr(payload['png'])).strip()
            if len(text) > 4000:
                raise ValueError('OCR 결과가 너무 깁니다. 영역을 줄여 주세요.')
            capture = {'text': text}
        elif kind == 'clipboard':
            text = payload.get('text', '').strip()
            if len(text) > 4000:
                raise ValueError('클립보드 검사는 한 번에 4,000자까지 가능합니다.')
            capture = {'text': text}
        else:
            capture = capture_text(payload)
            text = capture.get('text', '')
        if not text:
            connection.send({'error': capture.get('error', '검사할 텍스트가 없습니다.')})
            return
        # Release the UIA deadline before doing potentially slow HTTP requests.
        connection.send({'phase': 'checking'})
        from app.checker import SpellCheckerEngine
        result = SpellCheckerEngine().check(text)
        connection.send({'result': result, 'selection_mode': 'none'})
    except Exception as exc:
        connection.send({'error': '검사 작업 오류: ' + str(exc)[:300]})
    finally:
        connection.close()
