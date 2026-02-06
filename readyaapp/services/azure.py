import azure.cognitiveservices.speech as speechsdk
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

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    ssml = f"""
    <speak version="1.0" xml:lang="{lang}">
      <voice name="{voice}">
        {text}
      </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(result.cancellation_details.error_details)
