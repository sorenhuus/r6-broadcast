# r6-broadcast

Turn a recorded Rainbow Six Siege match into a TV-style broadcast with AI casters.

## Pipeline

1. **Record** – play the replay in-game, record with OBS (1080p, 60 fps, game audio only).
2. **Detect** – sample frames, OCR the kill feed / round timer / score → `events.json`.
3. **Commentate** – Claude writes play-by-play + analyst dialogue from the events.
4. **Voice** – Azure TTS renders two caster voices.
5. **Edit** – ffmpeg cuts highlights, adds scorebug, ducks game audio under casters.

## Quick start

```bash
pip install -e .
cp .env.example .env   # add ANTHROPIC_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
r6cast run matches/my_match.mp4 --out out/
```

Each stage can also run alone: `r6cast detect`, `r6cast commentate`, `r6cast voice`, `r6cast edit`.

## Requirements

- Python 3.11+
- ffmpeg on PATH
- Tesseract OCR (`winget install UB-Mannheim.TesseractOCR` on Windows)
