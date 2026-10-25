# Stadium Bravo, 2026-10-24 (Overwolf POV + AI casters)

How the video was made:
1. **Source.** Overwolf Insights recording (2560x720; game area cropped to 1706x720) plus the match `.rec` files.
2. **Events.** r6-dissect reads the kill feed. Video sync uses OCR on the HUD round clock: action starts at 103 / 339 / 546 s.
3. **Script.** 78 hand-anchored lines for two casters (`script.json`, t = video seconds).
4. **Voices.** Piper offline TTS: `en-us-ryan-high` for play-by-play, `en-us-lessac-medium` for the analyst.
5. **Render.** On the PC with ffmpeg: letterbox the game area to 1920x1080 with a LIVE bar and scorebug, use the game-only audio stream with sidechain ducking under the casters, and render in chunks under 180 s.
