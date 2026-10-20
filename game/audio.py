"""Sound system with overlapping effects and looping background music.

Backends, tried in this order:
  1. pygame.mixer  (optional `pip install pygame`) - mixes many sounds, real volume control, any platform
  2. Windows MCI   (ctypes, nothing to install)     - overlapping effects + a loop that effects no longer cut off
  3. winsound / afplay / aplay / paplay             - one sound at a time (the old behaviour)
Sound effects come from Taisei Project and Touhou Pixel Dungeon (see CREDITS.txt).
"""
from pathlib import Path
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sfx"
MUSIC_DIR = Path(__file__).resolve().parent / "assets" / "music"
_MUSIC = None
_LAST = {}
MASTER = 1.0
MUSIC_VOL = 1.0
SFX_VOL = 1.0
MUTED = False
_BACKEND = None
_Q = queue.Queue()


def _path(name):
    p = SOUND_DIR / f"{name}.wav"
    return str(p) if p.exists() else None


# ------------------------------------------------------------------ backend 1: pygame
class _Pygame:
    name = "pygame"

    def __init__(self):
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(24)
        self.pg, self.cache = pygame, {}

    def _snd(self, path):
        s = self.cache.get(path)
        if s is None:
            s = self.cache[path] = self.pg.mixer.Sound(path)
        return s

    def play(self, path, vol):
        s = self._snd(path)
        s.set_volume(max(0.0, min(1.0, vol * (0.0 if MUTED else MASTER * SFX_VOL))))
        s.play()

    def music(self, path, vol):
        m = self.pg.mixer.music
        try:
            m.fadeout(500)
            if path:
                m.load(path)
                m.set_volume(max(0.0, min(1.0, vol * (0.0 if MUTED else MASTER * MUSIC_VOL))))
                m.play(-1, fade_ms=1500)
        except Exception:
            pass

    def set_volumes(self):
        master = 0.0 if MUTED else MASTER
        try:
            self.pg.mixer.music.set_volume(max(0.0, min(1.0, master * MUSIC_VOL)))
        except Exception:
            pass

    def tick(self):
        pass


# ------------------------------------------------------------------ backend 2: Windows MCI
class _MCI:
    name = "mci"

    def __init__(self):
        import ctypes
        self.send = ctypes.windll.winmm.mciSendStringW
        self.buf = ctypes.create_unicode_buffer(128)
        self.opened, self.rr = {}, {}
        if self.cmd("open new type waveaudio alias _probe") not in (0, 263):
            pass
        self.cmd("close _probe")

    def cmd(self, s):
        return self.send(s, self.buf, 127, 0)

    def play(self, path, vol):
        k = self.rr[path] = (self.rr.get(path, -1) + 1) % 3          # up to 3 overlapping voices per effect
        alias = f"s{abs(hash(path)) % 10**8}_{k}"
        if alias not in self.opened:
            if self.cmd(f'open "{path}" type waveaudio alias {alias}') != 0:
                raise OSError("mci open failed")
            self.opened[alias] = True
        self.cmd(f"setaudio {alias} volume to {int(max(0.0, min(1.0, vol * (0.0 if MUTED else MASTER * SFX_VOL))) * 1000)}")
        self.cmd(f"seek {alias} to start")
        self.cmd(f"play {alias}")

    def music(self, path, vol):
        self.cmd("close bgm")
        self.bgm = None
        if path and self.cmd(f'open "{path}" type mpegvideo alias bgm') == 0:
            self.cmd(f"setaudio bgm volume to {int(max(0.0, min(1.0, vol * (0.0 if MUTED else MASTER * MUSIC_VOL))) * 1000)}")
            self.cmd("play bgm")
            self.bgm = path

    def set_volumes(self):
        master = 0.0 if MUTED else MASTER
        try:
            if getattr(self, "bgm", None):
                self.cmd(f"setaudio bgm volume to {int(max(0.0, min(1.0, master * MUSIC_VOL)) * 1000)}")
            for alias in self.opened:
                if alias == "bgm":
                    continue
                self.cmd(f"setaudio {alias} volume to {int(max(0.0, min(1.0, master * SFX_VOL)) * 1000)}")
        except Exception:
            pass

    def tick(self):
        """MCI cannot loop an mp3 by itself reliably: restart it when it has stopped."""
        if getattr(self, "bgm", None):
            self.cmd("status bgm mode")
            if self.buf.value == "stopped":
                self.cmd("play bgm from 0")


# ------------------------------------------------------------------ backend 3: one sound at a time
class _Basic:
    name = "basic"

    def __init__(self):
        self.ws = None
        if sys.platform == "win32":
            import winsound
            self.ws = winsound
        self.cli = next((c for c in ("afplay", "paplay", "aplay") if shutil.which(c)), None)
        if not self.ws and not self.cli:
            raise OSError("no audio player")

    def play(self, path, vol):
        if self.ws:
            self.ws.PlaySound(path, self.ws.SND_FILENAME | self.ws.SND_ASYNC | self.ws.SND_NODEFAULT)
        else:
            subprocess.Popen([self.cli, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def music(self, path, vol):
        pass                                      # a single-voice backend cannot mix music with effects

    def set_volumes(self):
        pass

    def tick(self):
        pass


def _worker():
    """All device calls run on one thread so the Tk game loop never waits for audio."""
    global _BACKEND
    for cls in (_Pygame, _MCI, _Basic):
        try:
            _BACKEND = cls()
            break
        except Exception:
            continue
    while True:
        try:
            job = _Q.get(timeout=0.5)
        except queue.Empty:
            if _BACKEND is not None:
                try:
                    _BACKEND.tick()
                except Exception:
                    pass
            continue
        if _BACKEND is None:
            continue
        try:
            if job[0] == "sfx":
                _BACKEND.play(job[1], job[2])
            elif job[0] == "mus":
                _BACKEND.music(job[1], job[2])
            elif job[0] == "vol":
                _BACKEND.set_volumes()
        except Exception:
            pass


threading.Thread(target=_worker, name="audio", daemon=True).start()


def configure_audio(master=1.0, music=1.0, sfx=1.0, muted=False):
    """Apply user-facing audio sliders immediately."""
    global MASTER, MUSIC_VOL, SFX_VOL, MUTED
    MASTER = max(0.0, min(1.0, float(master)))
    MUSIC_VOL = max(0.0, min(1.0, float(music)))
    SFX_VOL = max(0.0, min(1.0, float(sfx)))
    MUTED = bool(muted)
    _Q.put(("vol",))


def play_sound(name, volume=1.0, min_interval=0.045):
    """Queue a short effect. Repeats of the same effect closer than min_interval are dropped."""
    now = time.monotonic()
    if now - _LAST.get(name, -999) < min_interval:
        return
    _LAST[name] = now
    path = _path(name)
    if path:
        _Q.put(("sfx", path, volume))


def play_music(name, volume=0.55):
    """Start a looping music track (assets/music/<name>.mp3); asking for the one already playing does nothing."""
    global _MUSIC
    if name == _MUSIC:
        return
    p = MUSIC_DIR / f"{name}.mp3"
    if not p.exists():
        return
    _MUSIC = name
    _Q.put(("mus", str(p), volume))


def stop_music():
    global _MUSIC
    _MUSIC = None
    _Q.put(("mus", None, 0))
