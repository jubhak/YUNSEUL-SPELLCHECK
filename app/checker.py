import re
import json
import time
import requests
from html import unescape
from app.offline_rules import check_offline, OFFLINE_WORD_DICT, apply_refinement_rules

class SpellCheckerEngine:
    def __init__(self):
        self.base_url = "https://m.search.naver.com/p/csearch/ocontent/util/SpellerProxy"
        self.search_url = "https://search.naver.com/search.naver?where=nexearch&query=%EB%A7%9E%EC%B6%94%EB%B2%95%EA%B2%80%EC%82%AC%EA%B8%B0"
        self.passport_key = None
        self.key_timestamp = 0
        self.type_info = {
            'red_text': {'name': '맞춤법', 'color': '#E53E3E', 'badge_bg': '#FFF5F5', 'icon': '🔴'},
            'green_text': {'name': '띄어쓰기', 'color': '#2F855A', 'badge_bg': '#F0FFF4', 'icon': '🟢'},
            'blue_text': {'name': '표준어 의심', 'color': '#2B6CB0', 'badge_bg': '#EBF8FF', 'icon': '🔵'},
            'purple_text': {'name': '통계적 교정', 'color': '#6B46C1', 'badge_bg': '#FAF5FF', 'icon': '🟣'},
            'violet_text': {'name': '통계적 교정', 'color': '#6B46C1', 'badge_bg': '#FAF5FF', 'icon': '🟣'},
        }

    def get_passport_key(self, force_refresh=False):
        if not force_refresh and self.passport_key and (time.time() - self.key_timestamp < 7200):
            return self.passport_key

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            resp = requests.get(self.search_url, headers=headers, timeout=2.5)
            match = re.search(r'passportKey=([a-f0-9]+)', resp.text)
            if match:
                self.passport_key = match.group(1)
                self.key_timestamp = time.time()
                return self.passport_key
        except Exception:
            pass

        return self.passport_key or "bd7bcc12595f20e9f0a694d4e6b7eec40b8f8fca"

    def check(self, text: str) -> dict:
        text = text.strip()
        if not text:
            return {
                'success': True,
                'is_offline': False,
                'err_count': 0,
                'original': '',
                'corrected': '',
                'items': [],
                'counts': {'맞춤법': 0, '띄어쓰기': 0, '표준어 의심': 0, '통계적 교정': 0}
            }

        try:
            # Naver Speller has a 500-char limit per request
            if len(text) > 480:
                return self._check_chunks(text)
            return self._check_single(text)
        except Exception as e:
            print(f"[SpellChecker] Network check failed, switching to offline engine: {e}")
            return check_offline(text)

    def _check_single(self, text: str, retry=True) -> dict:
        key = self.get_passport_key()
        params = {
            'passportKey': key,
            '_callback': 'spellerCallback',
            'q': text,
            'where': 'nexearch',
            'color_blindness': 0
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://search.naver.com/'
        }

        try:
            resp = requests.get(self.base_url, params=params, headers=headers, timeout=2.5)
            if resp.status_code != 200:
                if retry:
                    self.get_passport_key(force_refresh=True)
                    return self._check_single(text, retry=False)
                return check_offline(text)

            m = re.search(r'spellerCallback\((.*)\);', resp.text)
            if not m:
                if retry:
                    self.get_passport_key(force_refresh=True)
                    return self._check_single(text, retry=False)
                return check_offline(text)

            data = json.loads(m.group(1))
            res = data.get('message', {}).get('result', {})
            return self._parse_result(text, res)

        except Exception as e:
            if retry:
                try:
                    self.get_passport_key(force_refresh=True)
                    return self._check_single(text, retry=False)
                except Exception:
                    pass
            return check_offline(text)

    def _check_chunks(self, text: str) -> dict:
        chunks = [text[i:i + 450] for i in range(0, len(text), 450)]

        combined_corrected = []
        combined_items = []
        total_err_count = 0
        counts = {'맞춤법': 0, '띄어쓰기': 0, '표준어 의심': 0, '통계적 교정': 0}
        any_offline = False

        for chunk in chunks:
            chunk_res = self._check_single(chunk)
            if chunk_res.get('is_offline'):
                any_offline = True
            combined_corrected.append(chunk_res['corrected'])
            combined_items.extend(chunk_res['items'])
            total_err_count += chunk_res['err_count']
            for k, v in chunk_res['counts'].items():
                counts[k] = counts.get(k, 0) + v

        return {
            'success': True,
            'is_offline': any_offline,
            'err_count': total_err_count,
            'original': text,
            'corrected': "".join(combined_corrected),
            'items': combined_items,
            'counts': counts
        }

    def _parse_result(self, original_text: str, result: dict) -> dict:
        err_count = result.get('errata_count', 0)
        origin_html = result.get('origin_html', '')
        html = result.get('html', '')
        notag = result.get('notag_html', original_text)

        items = []
        counts = {'맞춤법': 0, '띄어쓰기': 0, '표준어 의심': 0, '통계적 교정': 0}

        corr_matches = list(re.finditer(r"<em class='([^']+)'>([^<]+)</em>", html))
        orig_matches = list(re.finditer(r"<span class='result_underline'>([^<]+)</span>", origin_html))

        if len(corr_matches) == len(orig_matches) and len(corr_matches) > 0:
            for orig_m, corr_m in zip(orig_matches, corr_matches):
                cls = corr_m.group(1)
                meta = self.type_info.get(cls, {'name': '기타교정', 'color': '#718096', 'badge_bg': '#EDF2F7', 'icon': '✏️'})
                cat_name = meta['name']
                counts[cat_name] = counts.get(cat_name, 0) + 1

                orig_word = unescape(orig_m.group(1))
                corr_word = unescape(corr_m.group(2))

                guide_tip = ""
                if orig_word in OFFLINE_WORD_DICT:
                    guide_tip = OFFLINE_WORD_DICT[orig_word][2]
                elif corr_word in OFFLINE_WORD_DICT:
                    guide_tip = OFFLINE_WORD_DICT[corr_word][2]

                if not guide_tip and cat_name == '띄어쓰기':
                    guide_tip = "문맥에 맞게 단어 사이를 띄어 쓰거나 붙여 씁니다."
                elif not guide_tip and cat_name == '맞춤법':
                    guide_tip = "표준어 규정 및 한글 맞춤법에 따른 올바른 표기입니다."

                items.append({
                    'type': cat_name,
                    'color': meta['color'],
                    'badge_bg': meta['badge_bg'],
                    'icon': meta['icon'],
                    'original': orig_word,
                    'corrected': corr_word,
                    'guide': guide_tip or ''
                })
        elif len(corr_matches) > 0:
            for corr_m in corr_matches:
                cls = corr_m.group(1)
                meta = self.type_info.get(cls, {'name': '교정', 'color': '#E53E3E', 'badge_bg': '#FFF5F5', 'icon': '🔴'})
                cat_name = meta['name']
                counts[cat_name] = counts.get(cat_name, 0) + 1
                corr_word = unescape(corr_m.group(2))

                items.append({
                    'type': cat_name,
                    'color': meta['color'],
                    'badge_bg': meta['badge_bg'],
                    'icon': meta['icon'],
                    'original': '...',
                    'corrected': corr_word,
                    'guide': '올바른 표준어 표기입니다.'
                })

        # Apply expert refinement rules ('안돼' -> '안 돼', etc.) on the result
        final_corrected = apply_refinement_rules(notag, items, counts)

        return {
            'success': True,
            'is_offline': False,
            'err_count': len(items),
            'original': original_text,
            'corrected': final_corrected,
            'items': items,
            'counts': counts,
            'html': html,
            'origin_html': origin_html
        }
