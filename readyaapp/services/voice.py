import logging
import os
import re
import uuid
import tempfile

import requests
from num2words import num2words
from openai import OpenAI

logger = logging.getLogger(__name__)

_ONES = {
    0: "ნული",    1: "ერთი",      2: "ორი",       3: "სამი",
    4: "ოთხი",    5: "ხუთი",      6: "ექვსი",     7: "შვიდი",
    8: "რვა",     9: "ცხრა",     10: "ათი",       11: "თერთმეტი",
   12: "თორმეტი", 13: "ცამეტი",  14: "თოთხმეტი", 15: "თხუთმეტი",
   16: "თექვსმეტი",17: "ჩვიდმეტი",18: "თვრამეტი",19: "ცხრამეტი",
}
_TENS = {
   20: "ოცი",       30: "ოცდაათი",    40: "ორმოცი",
   50: "ორმოცდაათი",60: "სამოცი",     70: "სამოცდაათი",
   80: "ოთხმოცი",   90: "ოთხმოცდაათი",
}
_HUNDREDS = {
    1: "ას",   2: "ორას",  3: "სამას", 4: "ოთხას",
    5: "ხუთას",6: "ექვსას",7: "შვიდას",8: "რვაას", 9: "ცხრაას",
}
_ORDINALS_KA = {
    1: "პირველ",      2: "მეორე",       3: "მესამე",      4: "მეოთხე",
    5: "მეხუთე",      6: "მეექვსე",     7: "მეშვიდე",     8: "მერვე",
    9: "მეცხრე",     10: "მეათე",      11: "მეთერთმეტე", 12: "მეთორმეტე",
   13: "მეცამეტე",   14: "მეთოთხმეტე",15: "მეთხუთმეტე", 16: "მეთექვსმეტე",
   17: "მეჩვიდმეტე", 18: "მეთვრამეტე",19: "მეცხრამეტე",  20: "მეოცე",
   30: "მეოცდამეათე",40: "მეორმოცე",  50: "მეორმოცდამეათე",
}

def _stem(s: str) -> str:
    return s[:-1] if s.endswith("ი") else s

def number_to_georgian(n: int) -> str:
    if n < 0: return "მინუს " + number_to_georgian(-n)
    if n <= 19: return _ONES[n]
    if n < 100:
        if n % 10 == 0: return _TENS[n]
        return _stem(_TENS[(n // 10) * 10]) + "და" + _ONES[n % 10]
    if n < 1_000:
        h, r = divmod(n, 100); base = _HUNDREDS[h]
        return (base + "ი") if r == 0 else (base + "და" + number_to_georgian(r))
    if n < 1_000_000:
        th, r = divmod(n, 1_000)
        prefix = "ათას" if th == 1 else _stem(number_to_georgian(th)) + " ათას"
        return (prefix + "ი") if r == 0 else (prefix + " " + number_to_georgian(r))
    if n < 1_000_000_000:
        m, r = divmod(n, 1_000_000)
        prefix = "მილიონ" if m == 1 else _stem(number_to_georgian(m)) + " მილიონ"
        return (prefix + "ი") if r == 0 else (prefix + " " + number_to_georgian(r))
    return str(n)

_CASE_SUFFIXES = [
    "ისთვის","იდანვე","ობით","ამდე","იდან","ზედ","ში","ზე","ით","ად","ის","მდე","მა","ას","ვე","ნი","თა","სა","ს",
]
_CASE_SUFFIX_SET = set(_CASE_SUFFIXES)

def _apply_case(word: str, suffix: str) -> str:
    if " " in word:
        head, tail = word.rsplit(" ", 1)
        return head + " " + _apply_case(tail, suffix)
    ends_i = word.endswith("ი"); stem = word[:-1] if ends_i else word
    if suffix == "ს": return stem + "ს"
    if suffix in ("ზე","ში","ით","ად","მა"): return stem + suffix
    if suffix == "ის": return stem + "ის"
    if suffix == "ას": return stem + "ას"
    if suffix in ("მდე","ამდე"): return stem + "ამდე"
    if suffix == "იდან": return (word + "დან") if ends_i else (word + "იდან")
    if suffix == "ისთვის": return (word + "სთვის") if ends_i else (word + "ისთვის")
    if suffix == "ობით": return stem + "ობით"
    return word + suffix

def _roman_to_int(s: str) -> int | None:
    vals = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    result = prev = 0
    for ch in reversed(s.upper()):
        v = vals.get(ch, 0); result += v if v >= prev else -v; prev = v
    return result if result > 0 else None

_ROMAN_CORE = r"M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"
_ROMAN_ORDINAL_RE = re.compile(rf"\b({_ROMAN_CORE})\b(?=\s+[\u10D0-\u10FF])", re.IGNORECASE)
_ROMAN_CASE_RE = re.compile(rf"\b({_ROMAN_CORE})-({'|'.join(_CASE_SUFFIXES)})\b", re.IGNORECASE)
_ROMAN_PLAIN_RE = re.compile(rf"\b(M{{1,4}}|CM|CD|D?C{{1,3}}|XC|XL|L?X{{1,3}}|IX|IV|VI{{1,3}}|II{{1,2}}|VIII|VII|VI|XI{{0,3}}|X{{2,3}})\b")

_PUNCT_MAP = str.maketrans({
    "\u2014":", ","\u2013":", ","\u2012":", ","\u00ab":'"',"\u00bb":'"',
    "\u201c":'"',"\u201d":'"',"\u201e":'"',"\u2018":"'","\u2019":"'",
    "\u2026":"...","\u00a0":" ",
})
_SUFFIX_PAT = "|".join(_CASE_SUFFIXES)

def detect_language(text: str) -> str:
    if re.search(r"[\u10D0-\u10FF]", text): return "ka"
    if re.search(r"[\u0400-\u04FF]", text): return "ru"
    return "en"

_VOICE_CONFIG = {
    "ka": {"language": "ka", "voice_id": "95d51f79-c397-46f9-b49a-23763d3eaa2d"},
    "en": {"language": "en", "voice_id": "f786b574-daa5-4673-aa0c-cbe3e8534c02"},
    "ru": {"language": "ru", "voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b"},
}
_WHISPER_LANG = {"ka": None, "en": "en", "ru": "ru"}
CARTESIA_MODEL_ID = "sonic-3"

def normalize_text(text: str, lang: str) -> str:
    text = text.translate(_PUNCT_MAP)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b(\d{1,3}(?:,\d{3})+)\b", lambda m: m.group().replace(",",""), text)
    if lang in ("ru","en"):
        return re.sub(r"\b\d+\b", lambda m: num2words(int(m.group()), lang=lang), text)
    def _dash_word(m):
        word = m.group(2)
        if word in _CASE_SUFFIX_SET: return m.group()
        return _stem(number_to_georgian(int(m.group(1)))) + word
    text = re.sub(r"\b(\d+)-([\u10D0-\u10FF]+)", _dash_word, text)
    text = re.sub(rf"\b(\d+)-({_SUFFIX_PAT})\b", lambda m: _apply_case(number_to_georgian(int(m.group(1))), m.group(2)), text)
    text = re.sub(r"\b(\d+)\s+([\u10D0-\u10FF]+)", lambda m: number_to_georgian(int(m.group(1))) + " " + m.group(2), text)
    text = re.sub(r"\b\d+\b", lambda m: number_to_georgian(int(m.group())), text)
    def _roman_ordinal(m):
        v = _roman_to_int(m.group(1))
        return (_ORDINALS_KA.get(v) or number_to_georgian(v)) if v else m.group()
    def _roman_case(m):
        v = _roman_to_int(m.group(1))
        if not v: return m.group()
        return _apply_case(_ORDINALS_KA.get(v) or number_to_georgian(v), m.group(2))
    text = _ROMAN_ORDINAL_RE.sub(_roman_ordinal, text)
    text = _ROMAN_CASE_RE.sub(_roman_case, text)
    text = _ROMAN_PLAIN_RE.sub(lambda m: number_to_georgian(_roman_to_int(m.group())) if _roman_to_int(m.group()) else m.group(), text)
    return text


def _map_whisper_to_original(
    whisper_words: list,
    original_words: list[str],
) -> list[dict]:
    n = len(original_words)
    m = len(whisper_words)

    if n == 0 or m == 0:
        return []

    result = []
    for i in range(n):
        start_chunk = int((i / n) * m)
        end_chunk = int(((i + 1) / n) * m) - 1
        s = max(0, min(start_chunk, m - 1))
        e = max(s, min(end_chunk, m - 1))

        result.append({
            "word": original_words[i],
            "start": round(whisper_words[s].start, 3),
            "end": round(whisper_words[e].end, 3),
        })

    return result


def _get_timestamps_whisper(
    file_path: str,
    lang: str,
    original_words: list[str],
) -> list[dict]:
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("OPENAI_API_KEY not set — skipping timestamps")
        return []

    client = OpenAI(api_key=openai_key)
    whisper_lang = _WHISPER_LANG.get(lang, None)

    try:
        with open(file_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=whisper_lang,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

        if not hasattr(response, "words") or not response.words:
            return []

        return _map_whisper_to_original(list(response.words), original_words)

    except Exception as e:
        logger.warning("Whisper alignment failed (non-fatal): %s", e)
        return []


def generate_voice(text: str, speed: float = 0.92) -> dict:
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY is not set")

    lang = detect_language(text)
    clean_text = normalize_text(text, lang)
    cfg = _VOICE_CONFIG[lang]

    original_words = clean_text.split()

    logger.debug("TTS → lang=%s | %s", lang, clean_text[:300])

    audio_resp = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "Authorization": f"Bearer {cartesia_key}",
            "Cartesia-Version": "2025-04-16",
            "Content-Type": "application/json",
        },
        json={
            "model_id": CARTESIA_MODEL_ID,
            "transcript": clean_text,
            "language": cfg["language"],
            "voice": {"mode": "id", "id": cfg["voice_id"], "speed": speed},
            "output_format": {
                "container": "mp3",
                "encoding": "mp3",
                "sample_rate": 44100,
            },
        },
        timeout=60,
    )
    audio_resp.raise_for_status()

    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(tempfile.gettempdir(), filename)
    with open(file_path, "wb") as f:
        f.write(audio_resp.content)

    word_timestamps = _get_timestamps_whisper(file_path, lang, original_words)

    return {
        "file_path": file_path,
        "filename": filename,
        "word_timestamps": word_timestamps,
    }