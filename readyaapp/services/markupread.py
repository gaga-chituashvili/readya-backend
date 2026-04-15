import requests
import os
import uuid
import re
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment
from num2words import num2words


def is_georgian(text):
    return bool(re.search(r'[\u10D0-\u10FF]', text))


def is_russian(text):
    return bool(re.search(r'[А-Яа-я]', text))


def split_long_sentences(text, max_length=400):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []

    for sentence in sentences:
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        chunks.append(sentence)

    return chunks



def add_pauses(text):
    text = re.sub(r'([.!?])', r'\1 ... ', text)
    text = re.sub(r'([,;:])', r'\1 .. ', text)
    return re.sub(r"\s+", " ", text).strip()



ROMAN_MAP = {
    'I': 1, 'V': 5, 'X': 10,
    'L': 50, 'C': 100,
    'D': 500, 'M': 1000
}


def roman_to_int(s):
    total = 0
    prev = 0

    for char in reversed(s):
        value = ROMAN_MAP.get(char, 0)
        if value < prev:
            total -= value
        else:
            total += value
        prev = value

    return total


def normalize_roman(text):
    def replace_roman(match):
        roman = match.group()
        try:
            return num2words(roman_to_int(roman))
        except:
            return roman

    return re.sub(r'\b[IVXLCDM]+\b', replace_roman, text)


def normalize_numbers(text):
    def replace_number(match):
        num = match.group()
        try:
            return num2words(int(num))
        except:
            return num

    return re.sub(r'\b\d+\b', replace_number, text)



def estimate_word_duration(word):
    base = 0.15
    length = len(word) * 0.04

    if re.search(r'[.,!?]', word):
        return base + length + 0.2

    return base + length


def smart_timestamps(words, duration):
    weights = [estimate_word_duration(w) for w in words]
    total = sum(weights)

    aligned = []
    current = 0.0

    for word, w in zip(words, weights):
        segment = (w / total) * duration

        aligned.append({
            "word": word,
            "start": round(current, 2),
            "end": round(current + segment, 2)
        })

        current += segment

    return aligned


def generate_voice_with_timestamps(text: str):
    cartesia_key = os.getenv("CARTESIA_API_KEY")

    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY not set")

    filename = f"{uuid.uuid4()}.mp3"
    file_path = Path(settings.MEDIA_ROOT) / filename

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    clean_text = re.sub(r"\s+", " ", text).strip()
    clean_text = add_pauses(clean_text)


    if not is_georgian(clean_text) and not is_russian(clean_text):
        clean_text = normalize_roman(clean_text)
        clean_text = normalize_numbers(clean_text)
        clean_text = clean_text.replace("%", " percent")
        clean_text = clean_text.replace("$", " dollars")

    chunks = split_long_sentences(clean_text)

    
    with open(file_path, "wb") as f:
        for i, chunk in enumerate(chunks):
            response = requests.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "Authorization": f"Bearer {cartesia_key}",
                    "Cartesia-Version": "2025-04-16",
                    "Content-Type": "application/json"
                },
                json={
                    "model_id": "sonic-3",
                    "transcript": chunk.strip(),
                    "voice": {
                        "mode": "id",
                        "id": "95d51f79-c397-46f9-b49a-23763d3eaa2d"
                    },
                    "output_format": {
                        "container": "mp3",
                        "encoding": "mp3",
                        "sample_rate": 44100
                    },
                    "generation_config": {
                        "speed": 0.92,
                        "volume": 1.0
                    }
                },
                timeout=(5, 30)
            )

            if response.status_code != 200:
                raise Exception(response.text)

            f.write(response.content)

            if i < len(chunks) - 1:
                f.write(b"\x00" * 5000)

    
    try:
        audio = AudioSegment.from_file(file_path)
        duration = len(audio) / 1000
    except:
        duration = 0

    words = re.findall(r"\b[\w\u10D0-\u10FF]+\b", clean_text)

    aligned_words = smart_timestamps(words, duration)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": aligned_words,
        "duration": round(duration, 2)
    }