"""The ring announcer's voice: Kokoro neural text-to-speech, run locally (no account, no network).

    assets/tts/.venv/bin/python competition/voice.py <voice> <speed> <text file> <out.wav>

Used by announce.mjs, which adds the arena echo with ffmpeg. Set up once (see assets/tts/README.md):
    uv venv --python 3.13 assets/tts/.venv && VIRTUAL_ENV=assets/tts/.venv uv pip install kokoro-onnx soundfile
    plus kokoro-v1.0.onnx and voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0).
"""
import pathlib
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

MODELS = pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'tts'

voice, speed, text_file, out = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
text = pathlib.Path(text_file).read_text().strip()
kokoro = Kokoro(str(MODELS / 'kokoro-v1.0.onnx'), str(MODELS / 'voices-v1.0.bin'))
samples, rate = kokoro.create(text, voice=voice, speed=speed, lang='en-us')
sf.write(out, samples, rate)
