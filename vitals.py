class VitalsSystem:
    def __init__(self, starting_strength=100):
        self.strength = starting_strength
        self.exertion = 0.0          # Accumulates from movement, attacks, and damage
        self.base_bpm = 65.0         # Resting heart rate
        self.current_bpm = 65.0
        self.fainted = False
        self.dead = False
        self.torch_tick_accum = 0.0

    @property
    def faint_threshold(self):
        # Stronger players can sustain a higher heart rate before blacking out
        return 165.0 + (self.strength * 0.15)

    @property
    def fatal_threshold(self):
        return 225.0 + (self.strength * 0.25)

    def add_exertion(self, amount):
        """Adds exertion scaled inversely by player strength."""
        if self.dead:
            return
        scale = 100.0 / max(25.0, float(self.strength))
        self.exertion += amount * scale
        self._recalculate_bpm()

    def _recalculate_bpm(self):
        self.current_bpm = self.base_bpm + self.exertion

        if self.current_bpm >= self.fatal_threshold:
            self.current_bpm = self.fatal_threshold
            self.dead = True
            self.fainted = True
        elif self.current_bpm >= self.faint_threshold and not self.fainted:
            self.fainted = True
        elif self.fainted and self.current_bpm <= (self.faint_threshold - 35.0):
            # Recover consciousness once heart rate drops safely below threshold
            self.fainted = False

    def update(self, dt, active_torch, time_scale=1.0):
        """
        Updates heart recovery and torch burn-down each frame.
        Returns a status event string if something notable happens (e.g., fainting, torch dimming).
        """
        if self.dead:
            return None

        event_msg = None
        eff_dt = dt * time_scale

        # 1. Exponential heart recovery (mirrors T2_UpdateHeart DRight6 decay)
        if self.exertion > 0:
            recovery_rate = 0.28 * (self.strength / 100.0)
            self.exertion = max(0.0, self.exertion - (self.exertion * recovery_rate + 2.5) * eff_dt)

        was_fainted = self.fainted
        self._recalculate_bpm()

        if self.dead:
            return "YOUR WEARY HEART HAS STOPPED! YOU HAVE PERISHED."
        if not was_fainted and self.fainted:
            return "OVEREXERTION! YOUR VISION FADES TO BLACK AS YOU FAINT..."
        if was_fainted and not self.fainted:
            return "YOU REGAIN CONSCIOUSNESS, GASPING FOR AIR."

        # 2. Torch Burn-Down (1 game minute = 60 seconds)
        if active_torch and active_torch.is_lit and active_torch.minutes_left > 0:
            self.torch_tick_accum += eff_dt
            while self.torch_tick_accum >= 60.0 and active_torch.minutes_left > 0:
                self.torch_tick_accum -= 60.0
                active_torch.minutes_left -= 1

                if active_torch.minutes_left == 0:
                    active_torch.is_lit = False
                    active_torch.proper_name = "DEAD"
                    active_torch.torch_range = 0
                    active_torch.magic_light = False
                    event_msg = "YOUR TORCH SPUTTERS OUT! YOU ARE IN PITCH DARKNESS!"
                elif active_torch.minutes_left <= 5:
                    # ROM $D1A6: When <= 5 mins remain, range dims and magic light fades
                    active_torch.torch_range = max(1, active_torch.minutes_left)
                    active_torch.magic_light = False
                    event_msg = "YOUR TORCH FLAME GROWS DIM AND FLICKERS..."

        return event_msg