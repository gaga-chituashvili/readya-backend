from elevenlabs.client import ElevenLabs
from django.conf import settings

client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

def text_to_mp3(text: str, output_path: str):
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_v3",
        output_format="mp3_22050_32",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
