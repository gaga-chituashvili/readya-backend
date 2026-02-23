from google.cloud import texttospeech
from google.oauth2 import service_account
import uuid
import os
from django.conf import settings
from pydub import AudioSegment
import re
import html

credentials = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_APPLICATION_CREDENTIALS
)

tts_client = texttospeech.TextToSpeechClient(credentials=credentials)


# -------- Text Split --------
def split_long_sentences(text, max_length=250):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []

    for sentence in sentences:
        while len(sentence) > max_length:
            chunks.append(sentence[:max_length])
            sentence = sentence[max_length:]
        chunks.append(sentence)

    return chunks


# -------- Timestamps --------
def approximate_word_timestamps(file_path, text):
    audio = AudioSegment.from_file(file_path)
    duration = len(audio) / 1000

    clean_text = re.sub(r"[^\w\sა-ჰ]", "", text)
    words_split = clean_text.split()

    if not words_split:
        return []

    segment = duration / len(words_split)

    words = []
    current = 0.0

    for word in words_split:
        words.append({
            "word": word,
            "start": round(current, 2),
            "end": round(current + segment, 2)
        })
        current += segment

    return words


# -------- Main Function --------
def generate_voice_with_timestamps(text: str):

    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    clean_text = " ".join(text.split())
    chunks = split_long_sentences(clean_text)

    full_audio = b""

    for chunk in chunks:

        escaped_text = html.escape(chunk)

        ssml_text = f"""
        <speak>
            <prosody rate="1.0" pitch="0%">
                {escaped_text}
            </prosody>
        </speak>
        """

        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="uk-UA",
            name="uk-UA-Chirp3-HD-Laomedeia"
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )

        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        full_audio += response.audio_content

    with open(file_path, "wb") as out:
        out.write(full_audio)

    words = approximate_word_timestamps(file_path, clean_text)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": words
    }
