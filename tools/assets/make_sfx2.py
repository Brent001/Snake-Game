"""Second batch of sound effects: decodes clips from the Touhou Pixel Dungeon (mp3) and Taisei (opus) archives with
ffmpeg, trims leading silence, caps the length, fades the tail and normalises.
    python tools/make_sfx2.py <pixel-dungeon sounds dir> <taisei sfx dir>"""
import os, subprocess, sys, wave
import numpy as np
PD, TS = sys.argv[1], sys.argv[2]
OUT = os.path.join(os.path.dirname(__file__), "..", "game", "assets", "sfx")
# game name: (source file, max seconds, peak)
M = {
 "step_grass": (PD + "/grass.mp3", .2, .5), "step_stone": (PD + "/step.mp3", .15, .45),
 "ui_open": (PD + "/scan.mp3", .4, .55), "ui_close": (PD + "/click.mp3", .1, .5), "node_alloc": (PD + "/mastery.mp3", 1.0, .6),
 "hp_low": (PD + "/health_warn.mp3", .8, .6), "zap": (PD + "/zap.mp3", .5, .6), "lightning": (PD + "/lightning.mp3", .5, .6),
 "burning": (PD + "/burning.mp3", .5, .55), "puff": (PD + "/puff.mp3", .5, .5), "water": (PD + "/water.mp3", .4, .55),
 "gas": (PD + "/gas.mp3", .5, .5), "gold": (PD + "/gold.mp3", .6, .6), "drink": (PD + "/drink.mp3", .4, .6),
 "ghost": (PD + "/ghost.mp3", .7, .55), "mimic": (PD + "/mimic.mp3", .6, .55), "door_open": (PD + "/door_open.mp3", .7, .6),
 "descend": (PD + "/descend.mp3", .9, .6), "secret": (PD + "/secret.mp3", .8, .55), "trap": (PD + "/trap.mp3", .5, .65),
 "debuff": (PD + "/debuff.mp3", .6, .55), "beacon": (PD + "/beacon.mp3", .5, .5), "evoke": (PD + "/evoke.mp3", .5, .55),
 "extend": (PD + "/extend.mp3", .6, .55), "challenge": (PD + "/challenge.mp3", 1.5, .7), "bee": (PD + "/bee.mp3", .5, .45),
 "graze": (TS + "/graze.opus", .1, .4), "powersurge": (TS + "/powersurge_start.opus", .8, .65), "extra_life": (TS + "/extra_life.opus", 1.2, .7),
 "spellclear": (TS + "/spellclear.opus", 1.5, .75), "laser": (TS + "/laser1.opus", .8, .6), "bomb_reimu": (TS + "/bomb_reimu_a.opus", 1.2, .7),
 "redirect": (TS + "/redirect.opus", .6, .55), "timeout": (TS + "/timeout1.opus", .7, .55), "bomb_marisa": (TS + "/bomb_marisa_a.opus", 1.2, .7),
}
for name, (src, mx, pk) in M.items():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "s16le", "-ac", "1", "-ar", "22050", "-"], capture_output=True, check=True).stdout
    d = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    loud = np.where(np.abs(d) > 0.01)[0]
    if len(loud):
        d = d[loud[0]:]
    d = d[:int(mx * 22050)].copy()
    f = min(len(d) // 4, int(.04 * 22050))
    d[-f:] *= np.linspace(1, 0, f)
    d = d / (np.abs(d).max() or 1) * pk
    w = wave.open(os.path.join(OUT, name + ".wav"), "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes((d * 32767).astype(np.int16).tobytes()); w.close()
print(len(M), "written")
