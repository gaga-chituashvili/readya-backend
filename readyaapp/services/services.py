import azure.cognitiveservices.speech as speechsdk
import uuid
import os
from django.conf import settings


import threading

def generate_voice_with_timestamps(text: str):

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY_KA,
        region=settings.AZURE_SPEECH_REGION_KA
    )

    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceResponse_RequestWordBoundary,
        "true"
    )

    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    words = []
    done = threading.Event()

    def word_boundary(evt):
        print("WORD EVENT:", evt.text)
        words.append({
            "word": evt.text,
            "start": evt.audio_offset / 10000000
        })

    def synthesis_completed(evt):
        done.set()

    synthesizer.synthesis_word_boundary.connect(word_boundary)
    synthesizer.synthesis_completed.connect(synthesis_completed)

    ssml = f"""
    <speak version="1.0" xml:lang="ka-GE">
        <voice name="ka-GE-EkaNeural">
            {text}
        </voice>
    </speak>
    """

    synthesizer.speak_ssml_async(ssml)

    done.wait()

    for i in range(len(words) - 1):
        words[i]["end"] = words[i + 1]["start"]

    if words:
        words[-1]["end"] = words[-1]["start"] + 0.5

    print("FINAL WORDS:", words)

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words": words
    }
