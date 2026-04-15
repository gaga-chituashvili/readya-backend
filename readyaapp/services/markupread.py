import requests
import os
import uuid
import re
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment


def split_long_sentences(text, max_length=400):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []

    for sentence in sentences:
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        chunks.append(sentence)

    return chunks


def generate_voice_with_timestamps(text: str):

    cartesia_key = os.getenv("CARTESIA_API_KEY")

    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY not set")

    filename = f"{uuid.uuid4()}.mp3"
    file_path = Path(settings.MEDIA_ROOT) / filename

  
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    clean_text = " ".join(text.split())
    chunks = split_long_sentences(clean_text)

    full_audio = b""

    
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip() + "..."

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
            full_audio += b"\x00" * 5000

   
    with open(file_path, "wb") as f:
        f.write(full_audio)

    
    audio = AudioSegment.from_file(file_path)
    duration = len(audio) / 1000

    words = re.findall(r"\b[\w\u10D0-\u10FF]+\b", clean_text)

    if not words:
        return {
            "audio_url": settings.MEDIA_URL + filename,
            "words": [],
            "duration": duration
        }

    segment = duration / len(words)

    aligned_words = []
    current = 0.0

    for word in words:
        aligned_words.append({
            "word": word,
            "start": round(current, 2),
            "end": round(current + segment, 2)
        })
        current += segment

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": aligned_words,
        "duration": round(duration, 2)
    }