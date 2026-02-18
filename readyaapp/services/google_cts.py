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


def text_to_mp3(text, output_path):
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")

    clean_text = " ".join(text.split())
    escaped_text = html.escape(clean_text)

    lang = detect_language(clean_text)
    voice_config = get_voice_config(lang)

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    data = {
        "input": {
            "ssml": f"""
            <speak>
                <prosody rate="1.05" pitch="0%">
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

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(audio_content))

    return output_path
