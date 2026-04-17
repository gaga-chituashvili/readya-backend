import requests
import os
import uuid
import re
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment
from num2words import num2words
import whisperx


DEVICE = "cpu"

ALIGN_MODEL, METADATA = whisperx.load_align_model(
    language_code="ka",
    device=DEVICE
)

# =========================
# TEXT SPLIT
# =========================
def split_text_smart(text):
    return re.split(r'(?<=[.,!?])\s+', text)


# =========================
# TIMELINE NORMALIZATION
# =========================
def normalize_timeline(words):
    if not words:
        return words

    first_valid = next(
        (w for w in words if (w["end"] - w["start"]) > 0.04),
        None
    )

    if first_valid:
        shift = first_valid["start"]

        for w in words:
            w["start"] = max(0, w["start"] - shift)
            w["end"] = max(0, w["end"] - shift)

    durations = [
        (w["end"] - w["start"]) for w in words if (w["end"] - w["start"]) > 0.01
    ]

    avg = sum(durations) / len(durations) if durations else 0.2

    MIN_DUR = avg * 0.4
    MAX_DUR = avg * 2.2

    for i, w in enumerate(words):
        dur = w["end"] - w["start"]

        if dur < MIN_DUR:
            w["end"] = w["start"] + MIN_DUR
        elif dur > MAX_DUR:
            w["end"] = w["start"] + MAX_DUR

        if i > 0:
            prev = words[i - 1]

            if w["start"] < prev["end"]:
                w["start"] = prev["end"]

            if w["end"] <= w["start"]:
                w["end"] = w["start"] + MIN_DUR

    return words


# =========================
# 🔥 DRIFT FIX (CRITICAL)
# =========================
def fit_timeline_to_audio(words, audio_duration):
    if not words:
        return words

    last_end = words[-1]["end"]

    if last_end == 0:
        return words

    scale = audio_duration / last_end

    for w in words:
        w["start"] *= scale
        w["end"] *= scale

        # clamp
        if w["end"] > audio_duration:
            w["end"] = audio_duration

    return words


# =========================
# ALIGNMENT
# =========================
def align_with_whisperx(audio_path, text):
    try:
        audio = whisperx.load_audio(audio_path)

        chunks = split_text_smart(text)

        segments = [
            {"text": chunk.strip(), "start": None, "end": None}
            for chunk in chunks if chunk.strip()
        ]

        aligned = whisperx.align(
            segments,
            ALIGN_MODEL,
            METADATA,
            audio,
            DEVICE
        )

        raw_words = aligned.get("word_segments") or []

        words = []

        for w in raw_words:
            word = w["word"].strip()

            start = float(w["start"])
            end = float(w["end"])

            if end <= start:
                end = start + 0.01

            words.append({
                "word": word,
                "start": start,
                "end": end
            })

        words = normalize_timeline(words)

        return words

    except Exception as e:

        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000

        return generate_word_timestamps(text, duration)


# =========================
# LANGUAGE DETECTION
# =========================
def detect_language(text):
    if re.search(r'[\u10D0-\u10FF]', text):
        return "ka"
    return "en"


# =========================
# ROMAN → INT
# =========================
def roman_to_int(s):
    roman_map = {
        'I': 1, 'V': 5, 'X': 10,
        'L': 50, 'C': 100,
        'D': 500, 'M': 1000
    }

    result = 0
    prev = 0

    for ch in reversed(s.upper()):
        val = roman_map.get(ch, 0)
        if val < prev:
            result -= val
        else:
            result += val
            prev = val

    return result if result > 0 else None


# =========================
# GEORGIAN NUMBERS
# =========================
def number_to_georgian(n):
    units = {
        0: "ნული", 1: "ერთი", 2: "ორი", 3: "სამი", 4: "ოთხი",
        5: "ხუთი", 6: "ექვსი", 7: "შვიდი", 8: "რვა", 9: "ცხრა",
        10: "ათი", 11: "თერთმეტი", 12: "თორმეტი", 13: "ცამეტი",
        14: "თოთხმეტი", 15: "თხუთმეტი", 16: "თექვსმეტი",
        17: "ჩვიდმეტი", 18: "თვრამეტი", 19: "ცხრამეტი",
        20: "ოცი", 30: "ოცდაათი", 40: "ორმოცი",
        50: "ორმოცდაათი", 60: "სამოცი", 70: "სამოცდაათი",
        80: "ოთხმოცი", 90: "ოთხმოცდაათი"
    }

    if n in units:
        return units[n]

    if n < 100:
        tens = (n // 10) * 10
        remainder = n % 10
        return units[tens] + "და" + units[remainder]

    return str(n)


# =========================
# NUMBER NORMALIZATION
# =========================
def normalize_numbers(text, lang="en"):

    def replace_roman(match):
        roman = match.group()
        value = roman_to_int(roman)

        if value:
            if lang == "ka":
                return number_to_georgian(value)
            return num2words(value, lang="en")
        return roman

    def replace_number(match):
        num = int(match.group())
        if lang == "ka":
            return number_to_georgian(num)
        return num2words(num, lang="en")

    text = re.sub(
        r'(?<!\w)[IVXLCDM]+(?!\w)',
        replace_roman,
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r'\b\d+\b', replace_number, text)

    return text


# =========================
# FALLBACK TIMESTAMPS
# =========================
def generate_word_timestamps(text, duration):
    tokens = re.findall(r"[\w\u10D0-\u10FF']+|[.,!?;]", text)

    if not tokens:
        return []

    step = duration / len(tokens)

    result = []
    current = 0.0

    for t in tokens:
        result.append({
            "word": t,
            "start": round(current, 3),
            "end": round(current + step, 3)
        })
        current += step

    return result


# =========================
# MAIN FUNCTION
# =========================
def generate_voice_with_timestamps(text: str):

    cartesia_key = os.getenv("CARTESIA_API_KEY")

    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY not set")

    filename = f"{uuid.uuid4()}.mp3"
    file_path = Path(settings.MEDIA_ROOT) / filename
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    lang = detect_language(text)
    clean_text = normalize_numbers(text.strip(), lang)

    response = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "Authorization": f"Bearer {cartesia_key}",
            "Cartesia-Version": "2025-04-16",
            "Content-Type": "application/json"
        },
        json={
            "model_id": "sonic-3",
            "transcript": clean_text,
            "voice": {
                "mode": "id",
                "id": "95d51f79-c397-46f9-b49a-23763d3eaa2d",
                "speed": 0.85 
            },
            "output_format": {
                "container": "mp3",
                "encoding": "mp3",
                "sample_rate": 44100
            }
        }
    )

    if response.status_code != 200:
        raise Exception(response.text)

    with open(file_path, "wb") as f:
        f.write(response.content)

    audio = AudioSegment.from_file(file_path)
    duration = len(audio) / 1000

    words = align_with_whisperx(str(file_path), clean_text)

    words = fit_timeline_to_audio(words, duration)

    for w in words:
        w["start"] = round(w["start"], 3)
        w["end"] = round(w["end"], 3)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": words,
        "duration": round(duration, 3)
    }