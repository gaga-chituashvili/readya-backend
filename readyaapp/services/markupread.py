import requests
import os
import uuid
import re
import torch
import torchaudio
from pathlib import Path
from django.conf import settings
from pydub import AudioSegment
from num2words import num2words

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# =========================
# MMS ALIGNER (lazy)
# =========================
_aligner_bundle = None

def get_aligner():
    global _aligner_bundle
    if _aligner_bundle is None:
        bundle = torchaudio.pipelines.MMS_FA
        model  = bundle.get_model(with_star=False).to(DEVICE)
        _aligner_bundle = (model, bundle)
    return _aligner_bundle


# =========================
# HELPERS
# =========================
def detect_language(text):
    return "ka" if re.search(r'[\u10D0-\u10FF]', text) else "en"


def roman_to_int(s):
    m = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = prev = 0
    for ch in reversed(s.upper()):
        v = m.get(ch, 0)
        result += v if v >= prev else -v
        prev = v
    return result if result > 0 else None


def number_to_georgian(n):
    units = {
        0:"ნული",1:"ერთი",2:"ორი",3:"სამი",4:"ოთხი",5:"ხუთი",
        6:"ექვსი",7:"შვიდი",8:"რვა",9:"ცხრა",10:"ათი",11:"თერთმეტი",
        12:"თორმეტი",13:"ცამეტი",14:"თოთხმეტი",15:"თხუთმეტი",
        16:"თექვსმეტი",17:"ჩვიდმეტი",18:"თვრამეტი",19:"ცხრამეტი",
        20:"ოცი",30:"ოცდაათი",40:"ორმოცი",50:"ორმოცდაათი",
        60:"სამოცი",70:"სამოცდაათი",80:"ოთხმოცი",90:"ოთხმოცდაათი",
    }
    if n in units:
        return units[n]
    if n < 100:
        return units[(n//10)*10] + "და" + units[n%10]
    return str(n)


def normalize_numbers(text, lang="en"):
    def rr(m):
        v = roman_to_int(m.group())
        return (number_to_georgian(v) if lang=="ka" else num2words(v,lang="en")) if v else m.group()
    def rn(m):
        n = int(m.group())
        return number_to_georgian(n) if lang=="ka" else num2words(n,lang="en")
    text = re.sub(r'(?<!\w)[IVXLCDM]+(?!\w)', rr, text, flags=re.IGNORECASE)
    return re.sub(r'\b\d+\b', rn, text)


def get_mp3_encoder_delay(mp3_path: str) -> float:
    try:
        with open(mp3_path, "rb") as f:
            data = f.read(4096)
        for tag in (b"Xing", b"Info"):
            pos = data.find(tag)
            if pos == -1:
                continue
            if data[pos+120:pos+124] != b"LAME":
                continue
            gp = pos + 141
            if gp + 3 > len(data):
                continue
            delay_samples = (data[gp] << 4) | (data[gp+1] >> 4)
            for i in range(len(data)-3):
                if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                    sr = {0:44100,1:48000,2:32000,3:0}.get((data[i+2]>>2)&0x3, 44100)
                    if sr:
                        return delay_samples / sr
    except Exception:
        pass
    return 576 / 44100


# =========================
# MMS ALIGNMENT
# =========================
def align_with_mms(mp3_path: str, text: str, encoder_delay: float) -> list:
    model, bundle = get_aligner()

    waveform, sr = torchaudio.load(mp3_path)
    if sr != bundle.sample_rate:
        waveform = torchaudio.transforms.Resample(sr, bundle.sample_rate)(waveform)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    waveform = waveform.to(DEVICE)

    words = text.strip().split()

    with torch.inference_mode():
        emission, _ = model(waveform)

    try:
        alignments, _ = bundle.get_aligner()(
            emission, bundle.get_tokenizer()(words)
        )
    except Exception:
        dur = waveform.shape[-1] / bundle.sample_rate
        return _uniform_fallback(words, dur)

    # frame → seconds — resampled waveform-ის sample count გამოვიყენოთ
    spf = waveform.shape[-1] / (emission.shape[1] * bundle.sample_rate)

    result = []
    for w, a in zip(words, alignments):
        start = max(0.0, a.start * spf - encoder_delay)
        end   = max(0.0, a.end   * spf - encoder_delay)
        result.append({
            "word":  w,
            "start": round(float(start), 3),
            "end":   round(float(end),   3),
        })

    return result


def _uniform_fallback(words, duration):
    step = duration / max(len(words), 1)
    return [
        {"word": w, "start": round(i*step, 3), "end": round((i+1)*step, 3)}
        for i, w in enumerate(words)
    ]


# =========================
# MAIN
# =========================
def generate_voice_with_timestamps(text: str):
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY not set")

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    mp3_path = Path(settings.MEDIA_ROOT) / filename

    lang       = detect_language(text)
    clean_text = normalize_numbers(text.strip(), lang)

    
    response = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "Authorization":    f"Bearer {cartesia_key}",
            "Cartesia-Version": "2025-04-16",
            "Content-Type":     "application/json",
        },
        json={
            "model_id":   "sonic-3",
            "transcript": clean_text,
            "voice": {
                "mode":  "id",
                "id":    "95d51f79-c397-46f9-b49a-23763d3eaa2d",
                "speed": 0.92,
            },
            "output_format": {
                "container":   "mp3",
                "encoding":    "mp3",
                "sample_rate": 44100,
            },
        },
    )

    if response.status_code != 200:
        raise Exception(f"Cartesia error {response.status_code}: {response.text}")

    with open(mp3_path, "wb") as f:
        f.write(response.content)

    
    encoder_delay = get_mp3_encoder_delay(str(mp3_path))

    
    words = align_with_mms(str(mp3_path), clean_text, encoder_delay)

    audio    = AudioSegment.from_mp3(str(mp3_path))
    duration = len(audio) / 1000

    return {
        "audio_url": settings.MEDIA_URL + filename,
        "words":     words,
        "duration":  round(duration, 3),
    }