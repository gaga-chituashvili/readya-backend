import requests
import os
import uuid
import re
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment
from num2words import num2words



ROMAN_MAP = {
    'I': 1, 'V': 5, 'X': 10, 'L': 50,
    'C': 100, 'D': 500, 'M': 1000
}

def roman_to_int(s):
    s = s.upper()
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



def detect_language(text):
    if re.search(r'[\u10D0-\u10FF]', text):
        return "ka"
    return "en"



def normalize_numbers(text, lang="en"):

    
    def replace_roman(match):
        return str(roman_to_int(match.group()))

    text = re.sub(r'\b[IVXLCDM]+\b', replace_roman, text)

   
    def replace_number(match):
        num = int(match.group())
        try:
            return num2words(num, lang=lang)
        except:
            return match.group()

    text = re.sub(r'\b\d+\b', replace_number, text)

    return text



def split_long_sentences(text, max_length=400):
    sentences = re.split(r'(?<=[.!?;,])\s+', text)
    chunks = []

    for sentence in sentences:
        sentence = sentence.strip()

        while len(sentence) > max_length:
            split_point = sentence.rfind(" ", 0, max_length)
            if split_point == -1:
                split_point = max_length

            chunks.append(sentence[:split_point])
            sentence = sentence[split_point:].strip()

        chunks.append(sentence)

    return chunks


def normalize_word_timestamps(words):
    normalized = []

    for w in words:
        start = w.get("start", 0)
        end = w.get("end", 0)

        if start > 50:
            start = start / 1000
        if end > 50:
            end = end / 1000

        normalized.append({
            "word": w.get("word"),
            "start": round(start, 3),
            "end": round(end, 3)
        })

    return normalized



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

    
    clean_text = clean_text.replace(",", ", ")
    clean_text = clean_text.replace(";", "; ")
    clean_text = clean_text.replace(":", ": ")

    chunks = split_long_sentences(clean_text)

    full_audio = b""

    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()

        response = requests.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "Authorization": f"Bearer {cartesia_key}",
                "Cartesia-Version": "2025-04-16",
                "Content-Type": "application/json"
            },
            json={
                "model_id": "sonic-3",
                "transcript": chunk,
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
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(response.text)

        full_audio += response.content

       
        if i < len(chunks) - 1:
            silence = AudioSegment.silent(duration=300)
            full_audio += silence.raw_data

    
    with open(file_path, "wb") as f:
        f.write(full_audio)

   
    audio = AudioSegment.from_file(file_path)
    duration = len(audio) / 1000

    
    words = re.findall(r"\b[\w\u10D0-\u10FF]+\b", clean_text)

    if not words:
        return {
            "audio_url": settings.MEDIA_URL + filename,
            "words": [],
            "duration": round(duration, 3)
        }

    
    segment = duration / len(words)

    aligned_words = []
    current = 0.0

    for word in words:
        aligned_words.append({
            "word": word,
            "start": current,
            "end": current + segment
        })
        current += segment

    aligned_words = normalize_word_timestamps(aligned_words)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": aligned_words,
        "duration": round(duration, 3)
    }