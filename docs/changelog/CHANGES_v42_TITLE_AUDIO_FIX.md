# v42 - Removed the old wav ambience system

The looping wav biome ambience (assets/sfx/amb_*.wav) was deprecated by the mp3 music and played over menu.mp3
on the title screen. It is now removed completely.

- game/audio.py: removed play_ambience/stop_ambience, the ambience() method of every backend, AMBIENCE_VOL;
  configure_audio() no longer takes an ambience argument.
- game/app.py, game/systems/menu.py: removed all ambience calls and the AMBIENCE row in Settings.
- game/settings.py, game/settings.json: removed ambience_volume (old settings files still load fine).
- Deleted game/assets/sfx/amb_*.wav (6 files).
- Visual biome particles (render/ambient.py, draw_ambience) are untouched - they are graphics, not sound.
