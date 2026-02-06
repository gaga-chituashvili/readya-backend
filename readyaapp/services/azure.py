# import azure.cognitiveservices.speech as speechsdk
# from django.conf import settings


# def text_to_mp3(text: str, output_path: str):
#     speech_config = speechsdk.SpeechConfig(
#         subscription=settings.AZURE_SPEECH_KEY,
#         region=settings.AZURE_SPEECH_REGION 
#     )

#     speech_config.set_speech_synthesis_output_format(
#         speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
#     )


#     speech_config.speech_synthesis_voice_name = "ka-GE-EkaNeural"

#     audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

#     synthesizer = speechsdk.SpeechSynthesizer(
#         speech_config=speech_config,
#         audio_config=audio_config
#     )

#     synthesizer.speak_text_async(text).get()




import azure.cognitiveservices.speech as speechsdk
from django.conf import settings


def detect_language(text: str) -> str:
    for char in text:
        if "\u10A0" <= char <= "\u10FF":
            return "ka"
    return "en"


def text_to_mp3(text: str, output_path: str):
    language = detect_language(text)

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY,
        region=settings.AZURE_SPEECH_REGION
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    if language == "ka":
        voice = "ka-GE-EkaNeural"
        lang_tag = "ka-GE"
    else:
        voice = "en-US-JennyNeural"
        lang_tag = "en-US"

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    ssml = f"""
    <speak version="1.0" xml:lang="{lang_tag}">
      <voice name="{voice}">
        <prosody rate="0.95">
          {text}
        </prosody>
      </voice>
    </speak>
    """

    synthesizer.speak_ssml_async(ssml).get()
