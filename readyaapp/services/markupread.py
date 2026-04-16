import requests
import os
import uuid
import re
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment
from num2words import num2words



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
# LANGUAGE DETECTION
# =========================
def detect_language(text):
    if re.search(r'[\u10D0-\u10FF]', text):
        return "ka"
    return "en"


# =========================
# NUMBER NORMALIZATION
# =========================
def normalize_numbers(text, lang="en"):

    def adjust_georgian_case(word, next_word):
        targets = ["თვე", "თვეში", "თვეს", "წელი", "წელს", "კაცი"]

        mapping = {
            "ერთი": "ერთ",
            "ორი": "ორ",
            "სამი": "სამ",
            "ოთხი": "ოთხ",
            "ხუთი": "ხუთ",
            "ექვსი": "ექვს",
            "შვიდი": "შვიდ",
            "რვა": "რვა",
            "ცხრა": "ცხრა",
            "ათი": "ათ",
            "თერთმეტი": "თერთმეტ",
            "თორმეტი": "თორმეტ",
            "ცამეტი": "ცამეტ",
            "თოთხმეტი": "თოთხმეტ",
            "თხუთმეტი": "თხუთმეტ",
            "თექვსმეტი": "თექვსმეტ",
            "ჩვიდმეტი": "ჩვიდმეტ",
            "თვრამეტი": "თვრამეტ",
            "ცხრამეტი": "ცხრამეტ",
            "ოცი": "ოც"
}

        if any(next_word.startswith(t) for t in targets):
            return mapping.get(word, word)

        return word

    def replace_roman(match):
        roman = match.group()
        value = roman_to_int(roman)

        if value:
            try:
                if lang == "ka":
                    return number_to_georgian(value)
                return num2words(value, lang="en")
            except:
                return roman

        return roman

    def replace_number(match):
        num = int(match.group())

        try:
            if lang == "ka":
                word = number_to_georgian(num)

                
                after = text[match.end():].strip().split(" ")
                next_word = re.sub(r'[^\w\u10D0-\u10FF]', '', after[0]) if after else ""

                word = adjust_georgian_case(word, next_word)

                return word

            return num2words(num, lang="en")

        except:
            return match.group()

    text = re.sub(
        r'(?<!\w)[IVXLCDM]+(?!\w)',
        replace_roman,
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r'(\d+)-ზე',
        lambda m: (
            number_to_georgian(int(m.group(1)))[:-1] + "ზე"
            if number_to_georgian(int(m.group(1))).endswith("ი")
            else number_to_georgian(int(m.group(1))) + "ზე"
        )
        if lang == "ka"
        else num2words(int(m.group(1)), lang="en"),
        text
    )

    text = re.sub(r'\b\d+\b', replace_number, text)

    return text
# =========================
# WORD TIMESTAMPS (FAST)
# =========================
def generate_word_timestamps(text, duration):
    tokens = re.findall(r"[\w\u10D0-\u10FF']+|[.,!?;]", text)

    if not tokens:
        return []

    vowels = set("aeiouAEIOUაეიოუ")

    weights = []
    total_weight = 0

    for t in tokens:
        if re.match(r"[.,!?;]", t):
            weight = 7.5  
        else:
            weight = 0

            for ch in t:
                if ch in vowels:
                    weight += 1.3
                else:
                    weight += 0.9

            # long word boost
            weight += min(len(t), 8) * 0.12

        weights.append(weight)
        total_weight += weight

   

    result = []
    cumulative = 0.0

    for t, weight in zip(tokens, weights):
        portion = weight / total_weight
        start = duration * cumulative
        cumulative += portion
        end = duration * cumulative

        result.append({
            "word": t,
            "start": start,
            "end": end
        })
    for w in result:
        w["start"] = round(w["start"], 3)
        w["end"] = round(w["end"], 3)

        



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

    clean_text = text.strip()
    lang = detect_language(clean_text)
    clean_text = normalize_numbers(clean_text, lang)

    # =========================
    # TTS (FAST API)
    # =========================
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
                "id": "95d51f79-c397-46f9-b49a-23763d3eaa2d"
                # "speed": 0.85
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

    # save audio
    with open(file_path, "wb") as f:
        f.write(response.content)

    # =========================
    # AUDIO DURATION
    # =========================
    audio = AudioSegment.from_file(file_path)
    duration = len(audio) / 1000  

    # =========================
    # FAST WORD TIMESTAMPS
    # =========================
    aligned_words = generate_word_timestamps(clean_text, duration)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": aligned_words,
        "duration": round(duration, 3)
    }


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