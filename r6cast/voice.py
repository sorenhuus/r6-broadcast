"""Render caster lines to audio with Azure Speech."""
from __future__ import annotations

import os
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

VOICES = {
    "en": {"PBP": "en-US-DavisNeural", "ANALYST": "en-GB-RyanNeural"},
    "da": {"PBP": "da-DK-JeppeNeural", "ANALYST": "da-DK-ChristelNeural"},
}
STYLE = {"PBP": ("excited", "+8%"), "ANALYST": ("chat", "+0%")}


def _ssml(voice: str, speaker: str, text: str) -> str:
    style, rate = STYLE[speaker]
    lang = voice[:5]
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">'
        f'<voice name="{voice}"><mstts:express-as style="{style}">'
        f'<prosody rate="{rate}">{text}</prosody></mstts:express-as></voice></speak>'
    )


def render(lines: list[dict], out_dir: Path, lang: str = "en") -> list[dict]:
    cfg = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"],
                                 region=os.environ["AZURE_SPEECH_REGION"])
    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for i, line in enumerate(lines):
        path = out_dir / f"line_{i:04d}.wav"
        synth = speechsdk.SpeechSynthesizer(cfg, speechsdk.audio.AudioOutputConfig(filename=str(path)))
        res = synth.speak_ssml_async(_ssml(VOICES[lang][line["speaker"]], line["speaker"], line["text"])).get()
        if res.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"TTS failed on line {i}: {res.reason}")
        rendered.append({**line, "file": str(path)})
    return rendered
