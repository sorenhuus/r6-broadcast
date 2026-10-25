# Design: automated director

Goal: from a Siege match replay, produce a broadcast-style video. The software chooses camera angles (player POVs, third person), records them and adds casters. It needs no manual editing.

## Stages

1. **Parse** (`r6cast parse`): read `.rec` files with r6-dissect. Output: players, operators, kills (killer, victim, headshot, time), plants/defuses and round results → `events.json`.
2. **Direct** (`r6cast direct`): build a shot list per round from the events.
   - Before each kill, cut to the killer's POV ~4 s ahead (lead time scales with action density).
   - Clutch (1vX): stay on the clutching player; switch to third person for the reveal.
   - Plant/defuse: third person on the planter/defuser.
   - Quiet periods: rotate among alive players with the most recent action, with a minimum shot length of 3 s to avoid jitter.
   - Output: `shots.json` = [{round, t_start, t_end, player_slot, view: pov|third}].
3. **Capture** (`r6cast capture`, runs on the Windows PC):
   - Opens the replay round in the Siege replay viewer.
   - Starts and stops OBS recording through obs-websocket.
   - Fires the camera-switch keys from `shots.json` on a clock synced to the replay timer.
   - Fallback mode, `--multipass`: record each round once per player POV (and third person), then cut entirely in ffmpeg. This is slower (≈10× playback) but frame-accurate and needs no live switching.
4. **Commentate**: Claude writes play-by-play and analyst lines from the events and shot list.
5. **Voice**: Azure TTS renders two caster voices.
6. **Edit**: ffmpeg assembles the shots, scorebug, kill-feed overlays, slow-mo replays of key kills, intro/outro and ducked game audio.

## Open questions

- Replay viewer keybinds for player switching and third person. These are read from `GameSettings.ini` or set during calibration.
- Anti-cheat: capture sends synthetic keystrokes to the game window. They're menu and spectator inputs only, but the BattlEye risk isn't zero. `--multipass` reduces the inputs to one per pass.
