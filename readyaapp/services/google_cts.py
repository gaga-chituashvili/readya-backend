import requests
import base64
import os
import html
import re


def detect_language(text):
    if re.search(r"[a-zA-Z]", text):
        return "en"
    return "uk"


def get_voice_config(lang):
    voices = {
        "en": {
            "languageCode": "en-US",
            "name": "en-US-Chirp3-HD-Achernar"
        },
        "uk": {
            "languageCode": "uk-UA",
            "name": "uk-UA-Chirp3-HD-Laomedeia"
        }
    }
    return voices.get(lang, voices["uk"])



def split_long_sentences(text, max_length=250):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []

    for sentence in sentences:
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        chunks.append(sentence)

    return chunks


def text_to_mp3(text, output_path):
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")

    clean_text = " ".join(text.split())
    lang = detect_language(clean_text)
    voice_config = get_voice_config(lang)

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"


    chunks = split_long_sentences(clean_text)

    full_audio = b""

    for chunk in chunks:
        escaped_text = html.escape(chunk)

        data = {
            "input": {
                "ssml": f"""
                <speak>
                    <prosody rate="1" pitch="0%">
                        {escaped_text}
                    </prosody>
                </speak>
                """
            },
            "voice": voice_config,
            "audioConfig": {
                "audioEncoding": "MP3"
            }
        }

        response = requests.post(url, json=data, timeout=20)

        if response.status_code != 200:
            raise Exception(response.text)

        audio_content = response.json()["audioContent"]
        full_audio += base64.b64decode(audio_content)

    with open(output_path, "wb") as f:
        f.write(full_audio)

    return output_path
