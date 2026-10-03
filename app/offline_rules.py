# -*- coding: utf-8 -*-
"""
한국어 정밀 띄어쓰기 및 맞춤법 규칙 엔진 (온/오프라인 공통 적용)
포털 맞춤법 검사기가 문맥 부재나 다의어로 인해 놓치기 쉬운
'안돼' -> '안 돼', '안해' -> '안 해' 등의 빈출 부정 부사 띄어쓰기 및 문법 규칙을 완벽하게 교정합니다.
"""

import re
from typing import List, Dict, Tuple

# 빈출 맞춤법 & 띄어쓰기 단어 사전
OFFLINE_WORD_DICT = {
    # 띄어쓰기
    "맞춤법검사": ("맞춤법 검사", "띄어쓰기", "명사와 명사는 띄어 쓰는 것이 원칙입니다."),
    "맞춤법검사를": ("맞춤법 검사를", "띄어쓰기", "명사와 명사는 띄어 씁니다."),
    "검사를합시다": ("검사를 합시다", "띄어쓰기", "체언(조사)과 용언은 띄어 씁니다."),
    "감기빨리": ("감기 빨리", "띄어쓰기", "명사와 부사는 띄어 씁니다."),
    "수고많으셨습니다": ("수고 많으셨습니다", "띄어쓰기", "명사와 형용사는 띄어 씁니다."),
    "밥먹고": ("밥 먹고", "띄어쓰기", "목적어와 서술어는 띄어 씁니다."),
    "잠자고": ("잠 자고", "띄어쓰기", "목적어와 서술어는 띄어 씁니다."),
    "공부열심히": ("공부 열심히", "띄어쓰기", "명사와 부사는 띄어 씁니다."),
    "잘부탁드립니다": ("잘 부탁드립니다", "띄어쓰기", "부사와 용언은 띄어 씁니다."),

    # 맞춤법 및 인사말/오타
    "안낭하세요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안낭하세여": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안낭하새요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안낭하십니까": ("안녕하십니까", "맞춤법", "정중한 인사말의 올바른 표기는 '안녕하십니까'입니다."),
    "안낭해": ("안녕해", "맞춤법", "인사말의 올바른 표기는 '안녕'입니다."),
    "안낭": ("안녕", "맞춤법", "인사말의 올바른 표기는 '안녕'입니다."),
    "안냥하세요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안냥하세여": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안냥하새요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안냥하십니까": ("안녕하십니까", "맞춤법", "정중한 인사말의 올바른 표기는 '안녕하십니까'입니다."),
    "안냥": ("안녕", "맞춤법", "인사말의 올바른 표기는 '안녕'입니다."),
    "안뇽하세요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안뇽하세여": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안뇽": ("안녕", "맞춤법", "인사말의 올바른 표기는 '안녕'입니다."),
    "안녕 하세요": ("안녕하세요", "띄어쓰기", "'안녕하세요'는 한 단어로 붙여 씁니다."),
    "안녕하새요": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안녕하세여": ("안녕하세요", "맞춤법", "인사말의 올바른 표기는 '안녕하세요'입니다."),
    "안녕히계세요": ("안녕히 계세요", "띄어쓰기", "'안녕히 계세요'는 띄어 씁니다."),
    "안녕히가세요": ("안녕히 가세요", "띄어쓰기", "'안녕히 가세요'는 띄어 씁니다."),
    "감사합니당": ("감사합니다", "맞춤법", "표준어 종결어미 '-습니다'가 올바른 표기입니다."),
    "감사해용": ("감사해요", "맞춤법", "표준어 종결어미 '-해요'가 올바른 표기입니다."),
    "고맙습니당": ("고맙습니다", "맞춤법", "표준어 종결어미 '-습니다'가 올바른 표기입니다."),
    "죄송합니당": ("죄송합니다", "맞춤법", "표준어 종결어미 '-습니다'가 올바른 표기입니다."),
    "수고하세용": ("수고하세요", "맞춤법", "표준어 종결어미 '-세요'가 올바른 표기입니다."),
    "수고하세여": ("수고하세요", "맞춤법", "표준어 종결어미 '-세요'가 올바른 표기입니다."),
    "좋은하루되세요": ("좋은 하루 되세요", "띄어쓰기", "각 단어는 띄어 쓰는 것이 원칙입니다."),
    "반갑습니당": ("반갑습니다", "맞춤법", "표준어 종결어미 '-습니다'가 올바른 표기입니다."),
    "낳으세요": ("나으세요", "맞춤법", "병이나 상처가 호전되는 것은 '낫다'의 어간을 따르므로 '나으세요'가 맞습니다. ('낳다'는 출산)"),
    "빨리낳으세요": ("빨리 나으세요", "맞춤법", "호전의 의미는 '나으세요'이며 부사와 띄어 씁니다."),
    "감기빨리낳으세요": ("감기 빨리 나으세요", "맞춤법", "올바른 맞춤법과 띄어쓰기 교정입니다."),
    "낳으면": ("나으면", "맞춤법", "병이 호전되는 것은 '나으면'입니다."),
    "낳길": ("낫길", "맞춤법", "병이 호전되는 것은 '낫길'입니다."),
    "뵈요": ("봬요", "맞춤법", "'뵈어요'의 준말은 '봬요'입니다."),
    "뵜습니다": ("뵀습니다", "맞춤법", "'뵈었습니다'의 준말은 '뵀습니다'입니다."),
    "됬다": ("됐다", "맞춤법", "'되었다'의 준말은 '됐다'입니다."),
    "됬어": ("됐어", "맞춤법", "'되었어'의 준말은 '됐어'입니다."),
    "됬": ("됐", "맞춤법", "'되었'의 준말은 '됐'입니다."),
    "됫": ("됐", "맞춤법", "'되었'의 준말은 '됐'입니다."),
    "되요": ("돼요", "맞춤법", "'되어요'의 줄임말은 '돼요'입니다. ('하'를 넣어 '하여'가 되면 '돼'가 맞음)"),
    "몇일": ("며칠", "맞춤법", "날짜나 지난 날을 뜻할 때는 '며칠'이 표준어입니다."),
    "어떻해": ("어떡해", "맞춤법", "'어떻게 해'의 준말은 '어떡해'가 맞습니다."),
    "어의없다": ("어이없다", "맞춤법", "어처구니가 없음을 뜻하는 말은 '어이없다'입니다."),
    "금새": ("금세", "맞춤법", "'금시에'의 준말이므로 '금세'가 맞습니다."),
    "왠일": ("웬일", "맞춤법", "'어찌 된 일'은 '웬일'이 맞습니다. ('왠'은 '왠지'에만 사용)"),
    "왠만하면": ("웬만하면", "맞춤법", "'웬만하면'이 올바른 표기입니다."),
    "바램": ("바람", "맞춤법", "마음으로 바라는 일은 '바람'이 표준어입니다."),
    "설레임": ("설렘", "맞춤법", "'설레다'의 명사형은 '설렘'입니다."),
    "일해라절해라": ("이래라저래라", "맞춤법", "'이래라저래라'가 올바른 표준어입니다."),
    "구지": ("굳이", "맞춤법", "고집을 부려 구태여를 뜻하는 말은 '굳이'입니다."),
    "들어나다": ("드러나다", "맞춤법", "겉으로 나타나는 것은 '드러나다'입니다."),
    "건들이지마": ("건드리지 마", "맞춤법", "'건드리다'가 기본형이며 보조용언은 띄어 씁니다."),
    "틈틈히": ("틈틈이", "맞춤법", "'틈틈이'가 맞습니다."),
    "곰곰히": ("곰곰이", "맞춤법", "'곰곰이'가 표준어입니다."),
    "깨끗히": ("깨끗이", "맞춤법", "'ㅅ' 받침 뒤 부사화 접미사는 '-이'로 적습니다."),
    "번번히": ("번번이", "맞춤법", "매번을 뜻할 때는 '번번이'입니다."),
    "일일히": ("일일이", "맞춤법", "하나하나 세세히는 '일일이'입니다."),
}

# 의존 명사 띄어쓰기 패턴
DEPENDENT_PATTERNS = [
    (r"([가-힣]+[ㄹ을])(수)(있다|있는|있어|있었|있으|없다|없는|없어|없었|없으|밖에)", r"\1 \2 \3", "의존 명사 '수'는 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(수)", r"\1 \2", "의존 명사 '수'는 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을ㄴ은는던])(것)(이다|이고|이며|이나|으로|은|는|이|을|과|도|만)?", r"\1 \2\3", "의존 명사 '것'은 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(줄)(알|모르)", r"\1 \2 \3", "의존 명사 '줄'은 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(줄)", r"\1 \2", "의존 명사 '줄'은 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(때)", r"\1 \2", "때를 나타내는 의존적 표현은 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을ㄴ은는던])(데)(가|를|에|는|도|가)?", r"\1 \2\3", "경우나 장소를 뜻하는 의존 명사 '데'는 띄어 씁니다."),
    (r"([가-힣]+[ㄴ은])(지)(오래|한참|몇|삼|이|일|이틀|달|년)", r"\1 \2 \3", "경과한 시간을 나타내는 의존 명사 '지'는 띄어 씁니다."),
    (r"([가-힣]+[ㄴ은는던ㄹ을])(바)(가|를|에|와|이다)?", r"\1 \2\3", "의존 명사 '바'는 앞말과 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(뿐)(이다|이고|이며)?", r"\1 \2\3", "관형사형 뒤에 오는 의존 명사 '뿐'은 띄어 씁니다."),
    (r"([가-힣]+[ㄹ을])(뻔)(했다|하다|했어)?", r"\1 \2\3", "의존 명사 '뻔'은 앞말과 띄어 씁니다."),
]

# 보조 용언 띄어쓰기 패턴
AUXILIARY_PATTERNS = [
    (r"([가-힣]+고)(싶다|싶어|싶은|싶었|싶네|싶으|싶지)", r"\1 \2", "보조 형용사 '싶다'는 본용언과 띄어 쓰는 것이 원칙입니다."),
    (r"([가-힣]+지)(마|마라|마세요|말고|말자|말아|마시오)", r"\1 \2", "보조 동사 '말다'는 본용언과 띄어 씁니다."),
    (r"([가-힣]+[어아])(보다|보세요|보자|봤다|보았다|보면)", r"\1 \2", "보조 동사 '보다'는 본용언과 띄어 쓰는 것이 원칙입니다."),
    (r"([가-힣]+[어아])(두다|두었다|뒀다|두세요|두자|두면)", r"\1 \2", "보조 동사 '두다'는 본용언과 띄어 씁니다."),
    (r"([가-힣]+[어아])(놓다|놓았다|놨다|놓으세요|놓자)", r"\1 \2", "보조 동사 '놓다'는 본용언과 띄어 씁니다."),
]

# 문장 부호 뒤 띄어쓰기 패턴
PUNCTUATION_PATTERNS = [
    (r"([,])([가-힣A-Za-z0-9])", r"\1 \2", "쉼표(,) 뒤에는 한 칸 띄어 씁니다."),
    (r"([.?!])([가-힣A-Za-z0-9])", r"\1 \2", "문장 종결 부호(. ? !) 뒤에는 한 칸 띄어 씁니다."),
]


def apply_refinement_rules(text: str, items: list, counts: dict) -> str:
    """
    온라인/오프라인 검사 결과에 대해 '안낭하세요' -> '안녕하세요',
    '안돼' -> '안 돼', '안해' -> '안 해', '않돼' -> '안 돼' 등의
    빈출 인사말 오타, 부정 부사 띄어쓰기 및 문법 규칙을 정밀 후처리(보정)합니다.
    """
    corrected = text

    # =========================================================================
    # 0. 인사말 오타 및 키보드 인접 오타 전수 교정 ('안낭하세요', '안 낭하세요' -> '안녕하세요')
    # =========================================================================
    greeting_rules = [
        # 안낭하세요, 안 낭하세요, 안냥하세요, 안뇽하세요, 안녕하새요, 안녕하세여 -> 안녕하세요
        (
            r"(?<![가-힣])안[ \t]*([녕낭냥뇽])([하해])([세새])([요여용])(?![가-힣])",
            "안녕하세요",
            "인사말의 올바른 표기는 '안녕하세요'입니다."
        ),
        # 안낭하십니까, 안 낭하십니까, 안냥하십니까 -> 안녕하십니까
        (
            r"(?<![가-힣])안[ \t]*([녕낭냥뇽])([하해])(십니까|시오)(?![가-힣])",
            "안녕하십니까",
            "정중한 인사말의 올바른 표기는 '안녕하십니까'입니다."
        ),
        # 안낭해, 안낭해요 -> 안녕해, 안녕해요
        (
            r"(?<![가-힣])안[ \t]*([낭냥뇽])(해|해요|한다|했다|할게)(?![가-힣])",
            r"안녕\2",
            "인사말의 올바른 표기는 '안녕'입니다."
        ),
        # 단독 '안낭', '안냥', '안뇽' -> '안녕'
        (
            r"(?<![가-힣])안[ \t]*([낭냥뇽])(?![가-힣])",
            "안녕",
            "인사말의 올바른 표기는 '안녕'입니다."
        ),
        # 안녕히 계세요 띄어쓰기 및 맞춤법
        (
            r"(?<![가-힣])안녕히[ \t]*계([세새])([요여])(?![가-힣])",
            "안녕히 계세요",
            "배웅/작별 인사의 올바른 표기는 '안녕히 계세요'입니다."
        ),
        # 안녕히 가세요 띄어쓰기 및 맞춤법
        (
            r"(?<![가-힣])안녕히[ \t]*가([세새])([요여])(?![가-힣])",
            "안녕히 가세요",
            "배웅/작별 인사의 올바른 표기는 '안녕히 가세요'입니다."
        ),
        # 감사합니당, 감사해용
        (
            r"(?<![가-힣])감사합니당(?![가-힣])",
            "감사합니다",
            "표준어 종결어미 '-습니다'가 올바른 표기입니다."
        ),
        (
            r"(?<![가-힣])감사해용(?![가-힣])",
            "감사해요",
            "표준어 종결어미 '-해요'가 올바른 표기입니다."
        ),
        # 고맙습니당
        (
            r"(?<![가-힣])고맙습니당(?![가-힣])",
            "고맙습니다",
            "표준어 종결어미 '-습니다'가 올바른 표기입니다."
        ),
        # 죄송합니당
        (
            r"(?<![가-힣])죄송합니당(?![가-힣])",
            "죄송합니다",
            "표준어 종결어미 '-습니다'가 올바른 표기입니다."
        ),
        # 수고하세용, 수고하세여
        (
            r"(?<![가-힣])수고하세[용여](?![가-힣])",
            "수고하세요",
            "표준어 종결어미 '-세요'가 올바른 표기입니다."
        ),
    ]

    # 포털 검사기가 엉뚱하게 교정한 기존 items 항목 먼저 정밀 업데이트
    for item in items:
        for pat, repl, tip in greeting_rules:
            orig_candidate = item.get('original', '')
            corr_candidate = item.get('corrected', '')
            if re.search(pat, orig_candidate) or re.search(pat, corr_candidate):
                fixed_val = re.sub(pat, repl, orig_candidate if re.search(pat, orig_candidate) else corr_candidate)
                if item.get('corrected') != fixed_val:
                    if item.get('type') == '띄어쓰기':
                        counts['띄어쓰기'] = max(0, counts.get('띄어쓰기', 1) - 1)
                        counts['맞춤법'] = counts.get('맞춤법', 0) + 1
                    item['type'] = '맞춤법'
                    item['color'] = '#E53E3E'
                    item['badge_bg'] = '#FFF5F5'
                    item['icon'] = '🔴'
                    item['corrected'] = fixed_val
                    item['guide'] = tip

    # 본문 텍스트 내 인사말 오타 치환
    for pat, repl, tip in greeting_rules:
        matches = list(re.finditer(pat, corrected))
        for m in matches:
            orig = m.group(0)
            fixed = re.sub(pat, repl, orig)
            if orig != fixed:
                found = False
                for it in items:
                    if it.get('original') == orig or it.get('corrected') == fixed or (orig in it.get('original', '')):
                        found = True
                        it['corrected'] = fixed
                        it['type'] = '맞춤법'
                        it['color'] = '#E53E3E'
                        it['badge_bg'] = '#FFF5F5'
                        it['icon'] = '🔴'
                        it['guide'] = tip
                        break
                if not found:
                    counts['맞춤법'] = counts.get('맞춤법', 0) + 1
                    items.append({
                        'type': '맞춤법',
                        'color': '#E53E3E',
                        'badge_bg': '#FFF5F5',
                        'icon': '🔴',
                        'original': orig,
                        'corrected': fixed,
                        'guide': tip
                    })
                corrected = re.sub(pat, repl, corrected)

    existing_origs = {it.get('original', '') for it in items}

    # =========================================================================
    # 1. '않' vs '안' 잘못된 부정 표기 교정 (않돼 -> 안 돼, 않해 -> 안 해 등)
    # =========================================================================
    anh_patterns = [
        (r"(?<![가-힣])않(돼|됐|됌|되|된|될|됨|됩|됬)([가-힣]*)(?![가-힣])", "돼", "'않'은 '아니하-'의 준말로 용언 어간이며, 부사로는 '안'을 띄어 씁니다."),
        (r"(?<![가-힣])않(해|해요|한다|했다|할래|하지|하고|하면)(?![가-힣])", None, "부정 부사로는 '안'을 띄어 써야 합니다. ('안 해')"),
        (r"(?<![가-힣])않(가|가요|간다|갔다|갈래|가지|가고)(?![가-힣])", None, "부정 부사로는 '안'을 띄어 써야 합니다. ('안 가')"),
        (r"(?<![가-힣])않(봐|봐요|본다|봤다|볼래|보지|보고)(?![가-힣])", None, "부정 부사로는 '안'을 띄어 써야 합니다. ('안 봐')"),
        (r"(?<![가-힣])않(먹|먹어|먹어요|먹는다|먹었다|먹을래)(?![가-힣])", None, "부정 부사로는 '안'을 띄어 써야 합니다. ('안 먹어')"),
        (r"(?<![가-힣])않(사|사요|산다|샀다|살래)(?![가-힣])", None, "부정 부사로는 '안'을 띄어 써야 합니다. ('안 사')"),
    ]
    for pat, fix_head, tip in anh_patterns:
        matches = list(re.finditer(pat, corrected))
        for m in matches:
            orig = m.group(0)
            tail = m.group(1)
            suffix = m.group(2) if len(m.groups()) >= 2 else ""
            if fix_head:
                if tail in ("되", "돼") and suffix in ("", "요", "서", "도", "야"):
                    fixed = f"안 돼{suffix}"
                elif tail in ("됬", "됐"):
                    fixed = f"안 됐{suffix}"
                elif tail in ("됌", "됨"):
                    fixed = f"안 됨{suffix}"
                else:
                    fixed = f"안 {tail}{suffix}"
            else:
                fixed = f"안 {tail}"

            if orig != fixed and orig not in existing_origs:
                existing_origs.add(orig)
                counts['맞춤법'] = counts.get('맞춤법', 0) + 1
                items.append({
                    'type': '맞춤법',
                    'color': '#E53E3E',
                    'badge_bg': '#FFF5F5',
                    'icon': '🔴',
                    'original': orig,
                    'corrected': fixed,
                    'guide': tip
                })
                corrected = re.sub(pat, fixed, corrected)

    # =========================================================================
    # 2. 안 + 되다/돼다 계열 전수 교정 (안돼, 안돼요, 안된다, 안됨, 안되는데 등)
    # =========================================================================
    def repl_an_doeda(m):
        orig_word = m.group(0)
        first = m.group(1)
        suffix = m.group(2)
        is_spelling_err = False

        # '되' vs '돼' 맞춤법 오타 교정
        if first == "되" and suffix in ("", "요", "서", "도", "야"):
            first = "돼"
            is_spelling_err = True
        elif first == "됬":
            first = "됐"
            is_spelling_err = True
        elif first == "됌":
            first = "됨"
            is_spelling_err = True

        fixed_word = f"안 {first}{suffix}"

        if orig_word != fixed_word and orig_word not in existing_origs:
            existing_origs.add(orig_word)
            cat = "맞춤법" if is_spelling_err else "띄어쓰기"
            counts[cat] = counts.get(cat, 0) + 1
            color = '#E53E3E' if cat == '맞춤법' else '#2F855A'
            bg = '#FFF5F5' if cat == '맞춤법' else '#F0FFF4'
            icon = '🔴' if cat == '맞춤법' else '🟢'

            tip = "부정 부사 '안'은 뒤의 용언과 띄어 쓰는 것이 원칙입니다. (예: '안 돼', '안 된다', '안 돼요')"
            if is_spelling_err:
                tip = "'되지 않아'의 준말은 '안 돼'이며, 부정 부사 '안'은 띄어 씁니다."

            items.append({
                'type': cat,
                'color': color,
                'badge_bg': bg,
                'icon': icon,
                'original': orig_word,
                'corrected': fixed_word,
                'guide': tip
            })

        return fixed_word

    pat_an_doeda = r"(?<![가-힣])안(돼|됐|됌|되|된|될|됨|됩|됬)([가-힣]*)(?![가-힣])"
    corrected = re.sub(pat_an_doeda, repl_an_doeda, corrected)

    # =========================================================================
    # 3. 기타 부정 부사 '안' + 기본 동사 계열 (안해, 안가, 안봐, 안먹어 등)
    # =========================================================================
    other_an_verbs = [
        (r"(?<![가-힣])안(해|해요|한다|했다|할래|하지|하고|하면)(?![가-힣])", r"안 \1", "부정 부사 '안'은 뒤의 용언과 띄어 씁니다. (예: '안 해', '안 해요')"),
        (r"(?<![가-힣])안(가|가요|간다|갔다|갈래|가지|가고)(?![가-힣])", r"안 \1", "부정 부사 '안'은 뒤의 용언과 띄어 씁니다. (예: '안 가', '안 가요')"),
        (r"(?<![가-힣])안(봐|봐요|본다|봤다|볼래|보지|보고)(?![가-힣])", r"안 \1", "부정 부사 '안'은 뒤의 용언과 띄어 씁니다. (예: '안 봐', '안 봐요')"),
        (r"(?<![가-힣])안(먹|먹어|먹어요|먹는다|먹었다|먹을래)(?![가-힣])", r"안 \1", "부정 부사 '안'은 뒤의 용언과 띄어 씁니다. (예: '안 먹어')"),
        (r"(?<![가-힣])안(사|사요|산다|샀다|살래)(?![가-힣])", r"안 \1", "부정 부사 '안'은 뒤의 용언과 띄어 씁니다."),
    ]
    for pat, repl, tip in other_an_verbs:
        matches = list(re.finditer(pat, corrected))
        for m in matches:
            orig = m.group(0)
            fixed = re.sub(pat, repl, orig)
            if orig != fixed and orig not in existing_origs:
                existing_origs.add(orig)
                counts['띄어쓰기'] = counts.get('띄어쓰기', 0) + 1
                items.append({
                    'type': '띄어쓰기',
                    'color': '#2F855A',
                    'badge_bg': '#F0FFF4',
                    'icon': '🟢',
                    'original': orig,
                    'corrected': fixed,
                    'guide': tip
                })
                corrected = re.sub(pat, repl, corrected)

    return corrected


def check_offline(text: str) -> dict:
    original = text
    corrected = text
    items = []
    counts = {'맞춤법': 0, '띄어쓰기': 0, '표준어 의심': 0, '통계적 교정': 0}

    # Step 1: 문장 부호 띄어쓰기
    for pattern, repl, tip in PUNCTUATION_PATTERNS:
        matches = list(re.finditer(pattern, corrected))
        if matches:
            for m in matches:
                orig_snippet = m.group(0)
                corr_snippet = re.sub(pattern, repl, orig_snippet)
                if orig_snippet != corr_snippet:
                    counts['띄어쓰기'] += 1
                    items.append({
                        'type': '띄어쓰기',
                        'color': '#2F855A',
                        'badge_bg': '#F0FFF4',
                        'icon': '🟢',
                        'original': orig_snippet,
                        'corrected': corr_snippet,
                        'guide': tip
                    })
            corrected = re.sub(pattern, repl, corrected)

    # Step 2: 단어 사전 기반 교정
    for typo, (fix, cat, tip) in OFFLINE_WORD_DICT.items():
        if typo in corrected:
            counts[cat] = counts.get(cat, 0) + 1
            color = '#E53E3E' if cat == '맞춤법' else '#2F855A'
            bg = '#FFF5F5' if cat == '맞춤법' else '#F0FFF4'
            icon = '🔴' if cat == '맞춤법' else '🟢'

            items.append({
                'type': cat,
                'color': color,
                'badge_bg': bg,
                'icon': icon,
                'original': typo,
                'corrected': fix,
                'guide': tip
            })
            corrected = corrected.replace(typo, fix)

    # Step 3: 의존 명사 띄어쓰기 규칙
    for pattern, repl, tip in DEPENDENT_PATTERNS:
        matches = list(re.finditer(pattern, corrected))
        for m in matches:
            orig_match = m.group(0)
            fix_match = re.sub(pattern, repl, orig_match)
            if orig_match != fix_match and orig_match not in [it['original'] for it in items]:
                counts['띄어쓰기'] += 1
                items.append({
                    'type': '띄어쓰기',
                    'color': '#2F855A',
                    'badge_bg': '#F0FFF4',
                    'icon': '🟢',
                    'original': orig_match,
                    'corrected': fix_match,
                    'guide': tip
                })
        corrected = re.sub(pattern, repl, corrected)

    # Step 4: 보조 용언 띄어쓰기 규칙
    for pattern, repl, tip in AUXILIARY_PATTERNS:
        matches = list(re.finditer(pattern, corrected))
        for m in matches:
            orig_match = m.group(0)
            fix_match = re.sub(pattern, repl, orig_match)
            if orig_match != fix_match and orig_match not in [it['original'] for it in items]:
                counts['띄어쓰기'] += 1
                items.append({
                    'type': '띄어쓰기',
                    'color': '#2F855A',
                    'badge_bg': '#F0FFF4',
                    'icon': '🟢',
                    'original': orig_match,
                    'corrected': fix_match,
                    'guide': tip
                })
        corrected = re.sub(pattern, repl, corrected)

    # Step 5: 정밀 후처리 규칙 ('안돼' -> '안 돼' 등)
    corrected = apply_refinement_rules(corrected, items, counts)

    # 연속 공백 정리
    corrected = re.sub(r' {2,}', ' ', corrected)

    return {
        'success': True,
        'is_offline': True,
        'err_count': len(items),
        'original': original,
        'corrected': corrected,
        'items': items,
        'counts': counts
    }
