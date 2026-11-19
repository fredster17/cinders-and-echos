import math
import random
import struct
import pygame
from maze import DIRS

SAMPLE_RATE = 22050


def _build_sound(samples_mono):
    """Converts a list of normalized floats (-1.0 to 1.0) into a stereo pygame.mixer.Sound."""
    buf = bytearray()
    for s in samples_mono:
        clamped = max(-1.0, min(1.0, s))
        val = int(clamped * 32767)
        buf.extend(struct.pack("<hh", val, val))
    return pygame.mixer.Sound(buffer=bytes(buf))


def _gen_tone(freq, duration, wave="sine", decay=6.0, volume=0.5, freq_end=None):
    n = int(SAMPLE_RATE * duration)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        prog = i / max(1, n)
        f = freq if freq_end is None else (freq + (freq_end - freq) * prog)
        phase += (2.0 * math.pi * f) / SAMPLE_RATE
        env = math.exp(-decay * prog) * volume
        if wave == "sine":
            val = math.sin(phase)
        elif wave == "square":
            val = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == "noise":
            val = random.uniform(-1.0, 1.0)
        else:
            val = math.sin(phase)
        out.append(val * env)
    return _build_sound(out)


def _gen_heartbeat():
    """Generates an authentic low-frequency 'lub-dub' heartbeat sample."""
    duration = 0.36
    n = int(SAMPLE_RATE * duration)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # First thump ("lub") around 0.03s
        lub = 0.0
        if t < 0.14:
            env1 = math.sin(math.pi * (t / 0.14)) ** 2
            lub = math.sin(2.0 * math.pi * 54.0 * t) * env1 * 0.85
        # Second thump ("dub") around 0.18s
        dub = 0.0
        if 0.15 <= t < 0.30:
            lt = t - 0.15
            env2 = math.sin(math.pi * (lt / 0.15)) ** 2
            dub = math.sin(2.0 * math.pi * 46.0 * lt) * env2 * 0.65
        out.append(lub + dub)
    return _build_sound(out)


class SoundEngine:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            return

        self.heartbeat_snd = _gen_heartbeat()
        self.sfx = {
            "STEP": _gen_tone(95, 0.09, wave="noise", decay=18.0, volume=0.35),
            "WALL_THUD": _gen_tone(110, 0.18, wave="sine", decay=12.0, volume=0.65, freq_end=45),
            "TORCH_LIGHT": _gen_tone(800, 0.28, wave="noise", decay=7.0, volume=0.45),
            "SWING": _gen_tone(320, 0.16, wave="noise", decay=10.0, volume=0.4, freq_end=120),
            "HIT": _gen_tone(160, 0.22, wave="square", decay=9.0, volume=0.55, freq_end=55),
            "KILL": _gen_tone(220, 0.45, wave="square", decay=4.5, volume=0.6, freq_end=40),
            "PLAYER_HIT": _gen_tone(130, 0.30, wave="square", decay=6.0, volume=0.7, freq_end=38),
            "FLASK": _gen_tone(440, 0.25, wave="sine", decay=6.0, volume=0.45, freq_end=680),
            "REVEAL": _gen_tone(520, 0.35, wave="sine", decay=4.0, volume=0.45, freq_end=880),
            # Creature signature audio cues
            "SPIDER": _gen_tone(1800, 0.14, wave="square", decay=14.0, volume=0.35, freq_end=900),
            "SNAKE": _gen_tone(2400, 0.26, wave="noise", decay=6.0, volume=0.4),
            "BLOB": _gen_tone(140, 0.28, wave="sine", decay=6.0, volume=0.5, freq_end=260),
            "GIANT": _gen_tone(75, 0.24, wave="sine", decay=9.0, volume=0.65, freq_end=42),
            "KNIGHT": _gen_tone(620, 0.20, wave="square", decay=10.0, volume=0.45, freq_end=410),
            "WRAITH": _gen_tone(540, 0.45, wave="sine", decay=3.5, volume=0.45, freq_end=720),
            "WIZARD": _gen_tone(240, 0.40, wave="square", decay=3.0, volume=0.45, freq_end=360),
        }

    def play(self, name, volume=0.8):
        if not self.enabled or name not in self.sfx:
            return
        snd = self.sfx[name]
        snd.set_volume(max(0.0, min(1.0, volume)))
        snd.play()

    def play_heartbeat(self, bpm, faint_threshold):
        if not self.enabled:
            return
        # Louder heartbeat as stress climbs
        stress = max(0.0, min(1.0, (bpm - 65.0) / max(1.0, (faint_threshold - 65.0))))
        vol = 0.30 + 0.65 * stress
        self.heartbeat_snd.set_volume(vol)
        self.heartbeat_snd.play()

    def play_spatial_monster(self, shape, mx, my, px, py, pdir):
        """Pans creature sound across left/right stereo channels based on player facing angle & distance."""
        if not self.enabled or shape not in self.sfx:
            return
        dx = mx - px
        dy = my - py
        dist = math.hypot(dx, dy)
        if dist > 6.5:
            return

        atten = max(0.08, (1.0 - (dist / 6.5)) ** 1.5)
        if dist < 0.1:
            left_vol = right_vol = atten
        else:
            fx, fy = DIRS[pdir]
            # Right-hand perpendicular vector
            rx, ry = -fy, fx
            nx, ny = dx / dist, dy / dist
            pan = nx * rx + ny * ry  # -1.0 = full left, +1.0 = full right
            left_vol = atten * math.sqrt(max(0.05, (1.0 - pan) * 0.5))
            right_vol = atten * math.sqrt(max(0.05, (1.0 + pan) * 0.5))

        ch = pygame.mixer.find_channel(True)
        if ch:
            ch.set_volume(left_vol, right_vol)
            ch.play(self.sfx[shape])