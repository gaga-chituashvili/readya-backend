import requests
import os
import re


def split_long_sentences(text, max_length=400):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []

    for sentence in sentences:
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        chunks.append(sentence)

    return chunks


def text_to_mp3(text, output_path, speed=0.92, voice_id=None):
    api_key = os.getenv("CARTESIA_API_KEY")

    if not api_key:
        raise ValueError("CARTESIA_API_KEY not set")

    clean_text = " ".join(text.split())

    DEFAULT_VOICE_ID = "95d51f79-c397-46f9-b49a-23763d3eaa2d"
    voice_id = voice_id or DEFAULT_VOICE_ID

    url = "https://api.cartesia.ai/tts/bytes"
    chunks = split_long_sentences(clean_text)

    full_audio = b""

    for i, chunk in enumerate(chunks):

       
        chunk = chunk.strip() + "..."

        payload = {
            "model_id": "sonic-3",
            "transcript": chunk,
            "voice": {
                "mode": "id",
                "id": voice_id
            },
            "output_format": {
                "container": "mp3",
                "encoding": "mp3",
                "sample_rate": 44100
            },
            "generation_config": {
                "speed": speed,  
                "volume": 1
            }
        }

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Cartesia-Version": "2025-04-16",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(f"{response.status_code} - {response.text}")

        full_audio += response.content


        if i < len(chunks) - 1:
            full_audio += b"\x00" * 5000

    with open(output_path, "wb") as f:
        f.write(full_audio)

    return output_path