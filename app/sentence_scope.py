"""Bounded sentence extraction; independent of Windows and Qt."""
import re

MAX_SENTENCE = 1000
CONTEXT_CHARS = 1024
MAX_VALUE = 4096
# A pragmatic Korean/Latin sentence boundary, not a linguistic parser.
_BOUNDARY = re.compile(r'[.!?。！？]+[\"\'”’」』)]*(?=\s|$)|[\r\n]+')


def sentence_at(text, caret, limit=MAX_SENTENCE):
    """Return only the sentence containing the caret; fail closed on long input.

    Whitespace immediately after punctuation belongs to the following sentence.
    At EOF (or immediately after punctuation) prefer the preceding sentence.
    """
    if not text:
        return ''
    caret = max(0, min(int(caret), len(text)))
    start = 0
    for match in _BOUNDARY.finditer(text):
        end = match.end()
        if caret <= end and (caret > start or start == 0):
            value = text[start:end].strip()
            return value if len(value) <= limit else ''
        start = end
    value = text[start:].strip()
    return value if len(value) <= limit else ''
