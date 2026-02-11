import requests
from django.conf import settings


def detect_language(text: str) -> str:
    return "ka" if any("\u10A0" <= c <= "\u10FF" for c in text) else "en"


def text_to_mp3(text: str, output_path: str):
    language = detect_language(text)

    if language == "ka":
        key = settings.AZURE_SPEECH_KEY_KA
        region = settings.AZURE_SPEECH_REGION_KA
        voice = "ka-GE-EkaNeural"
        lang = "ka-GE"
    else:
        key = settings.AZURE_SPEECH_KEY_EN
        region = settings.AZURE_SPEECH_REGION_EN
        voice = "en-US-AriaNeural"
        lang = "en-US"

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
        "User-Agent": "readya-app",
    }

    ssml = f"""
    <speak version="1.0" xml:lang="{lang}">
        <voice name="{voice}">
            {text}
        </voice>
    </speak>
    """

    response = requests.post(url, headers=headers, data=ssml.encode("utf-8"))

    if response.status_code != 200:
        raise RuntimeError(f"Azure TTS failed: {response.text}")

    with open(output_path, "wb") as f:
        f.write(response.content)
