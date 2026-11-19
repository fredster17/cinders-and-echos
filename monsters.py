import random
from maze import DIRS, OPEN, DOOR, MAGIC
from inventory import GameItem

MONSTER_SPECS = {
    "SPIDER":       {"hp": 12,  "atk": 16,  "move_cd": 1.1, "atk_cd": 1.8, "sound": "SKITTERING",   "magic": False, "ring_only": False, "loots": True,  "block": 0.0,  "shape": "SPIDER"},
    "VIPER":        {"hp": 22,  "atk": 30,  "move_cd": 1.25,"atk_cd": 1.6, "sound": "HISSING",      "magic": False, "ring_only": False, "loots": True,  "block": 0.0,  "shape": "SNAKE"},
    "SCORPION":     {"hp": 32,  "atk": 45,  "move_cd": 1.05,"atk_cd": 1.5, "sound": "CHITTERING",   "magic": False, "ring_only": False, "loots": False, "block": 0.1,  "shape": "SPIDER"},
    "SLIME BLOB":   {"hp": 52,  "atk": 55,  "move_cd": 2.2, "atk_cd": 2.4, "sound": "SQUELCHING",   "magic": False, "ring_only": False, "loots": True,  "block": 0.0,  "shape": "BLOB"},
    "CLUB GIANT":   {"hp": 48,  "atk": 58,  "move_cd": 2.5, "atk_cd": 2.5, "sound": "HEAVY STEPS",  "magic": False, "ring_only": False, "loots": True,  "block": 0.0,  "shape": "GIANT"},
    "HATCHET GIANT":{"hp": 72,  "atk": 76,  "move_cd": 2.1, "atk_cd": 2.2, "sound": "THUNDEROUS STEPS","magic": False,"ring_only": False,"loots": True,  "block": 0.1,  "shape": "GIANT"},
    "KNIGHT":       {"hp": 85,  "atk": 82,  "move_cd": 1.65,"atk_cd": 1.8, "sound": "CLANKING",     "magic": False, "ring_only": False, "loots": True,  "block": 0.15, "shape": "KNIGHT"},
    "SHIELD KNIGHT":{"hp": 105, "atk": 90,  "move_cd": 1.75,"atk_cd": 1.9, "sound": "HEAVY ARMOR",  "magic": False, "ring_only": False, "loots": True,  "block": 0.45, "shape": "KNIGHT"},
    "WRAITH":       {"hp": 115, "atk": 98,  "move_cd": 1.55,"atk_cd": 1.7, "sound": "EERIE WAIL",   "magic": True,  "ring_only": False, "loots": True,  "block": 0.0,  "shape": "WRAITH"},
    "DREAD OGRE":   {"hp": 150, "atk": 115, "move_cd": 1.7, "atk_cd": 1.8, "sound": "GROUND TREMOR","magic": False, "ring_only": False, "loots": True,  "block": 0.2,  "shape": "GIANT"},
    "DOPPELGANGER": {"hp": 130, "atk": 105, "move_cd": 1.6, "atk_cd": 1.7, "sound": "MOCKING WHISPER","magic": True,"ring_only": True,  "loots": False, "block": 0.0,  "shape": "WIZARD"},
    "ARCH-WARLOCK": {"hp": 210, "atk": 135, "move_cd": 1.7, "atk_cd": 1.5, "sound": "ARCANE HUM",   "magic": True,  "ring_only": False, "loots": False, "block": 0.25, "shape": "WIZARD"},
}


class Monster:
    def __init__(self, name, x, y):
        spec = MONSTER_SPECS[name]
        self.name = name
        self.max_hp = spec["hp"]
        self.hp = spec["hp"]
        self.atk = spec["atk"]
        self.move_interval = spec["move_cd"]
        self.atk_interval = spec["atk_cd"]
        self.sound_cue = spec["sound"]
        self.is_magical = spec["magic"]
        self.ring_only = spec["ring_only"]
        self.can_loot = spec["loots"]
        self.phys_block = spec["block"]
        self.shape = spec["shape"]

        self.x = x
        self.y = y
        self.dir = random.randint(0, 3)
        self.move_timer = random.uniform(0.5, self.move_interval)
        self.atk_timer = self.atk_interval * 0.75
        self.sound_timer = random.uniform(2.0, 5.0)
        self.held_items = []
        self.alive = True

    def can_see_player(self, level, px, py):
        if self.x == px and self.y == py:
            return True
        if self.x != px and self.y != py:
            return False

        dx = 0 if px == self.x else (1 if px > self.x else -1)
        dy = 0 if py == self.y else (1 if py > self.y else -1)
        dir_idx = DIRS.index((dx, dy))

        cx, cy = self.x, self.y
        while (cx, cy) != (px, py):
            if not level.is_open(cx, cy):
                return False
            wall = level.grid[cy][cx][dir_idx]
            if wall not in (OPEN, DOOR, MAGIC):
                return False
            cx += dx
            cy += dy
        return True

    def step_toward_player(self, level, px, py, all_monsters):
        dx = 0 if px == self.x else (1 if px > self.x else -1)
        dy = 0 if py == self.y else (1 if py > self.y else -1)
        nx, ny = self.x + dx, self.y + dy
        if not any(m.alive and m is not self and (m.x, m.y) == (nx, ny) for m in all_monsters):
            self.dir = DIRS.index((dx, dy))
            self.x, self.y = nx, ny

    def wander(self, level, all_monsters):
        valid_dirs = []
        for d, (dx, dy) in enumerate(DIRS):
            wall = level.grid[self.y][self.x][d]
            if wall in (OPEN, DOOR, MAGIC):
                nx, ny = self.x + dx, self.y + dy
                if not any(m.alive and m is not self and (m.x, m.y) == (nx, ny) for m in all_monsters):
                    valid_dirs.append(d)

        if not valid_dirs:
            return
        opp = (self.dir + 2) % 4
        non_reverse = [d for d in valid_dirs if d != opp]
        chosen = random.choice(non_reverse if non_reverse else valid_dirs)
        self.dir = chosen
        dx, dy = DIRS[chosen]
        self.x += dx
        self.y += dy

    def to_dict(self):
        data = self.__dict__.copy()
        data["held_items"] = [i.to_dict() for i in self.held_items]
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["name"], data["x"], data["y"])
        items = [GameItem.from_dict(i) for i in data.get("held_items", [])]
        obj.__dict__.update(data)
        obj.held_items = items
        return obj


def spawn_level_monsters(level):
    rng = random.Random(level.level_num + 101)
    open_coords = [
        (x, y) for y in range(level.size) for x in range(level.size)
        if level.is_open(x, y) and abs(x - level.spawn_pos[0]) + abs(y - level.spawn_pos[1]) > 3
    ]

    rosters = {
        0: ["SPIDER", "SPIDER", "VIPER", "VIPER", "SLIME BLOB", "CLUB GIANT", "CLUB GIANT"],
        1: ["VIPER", "SCORPION", "SLIME BLOB", "CLUB GIANT", "HATCHET GIANT", "KNIGHT", "KNIGHT"],
        2: ["SCORPION", "SCORPION", "HATCHET GIANT", "SHIELD KNIGHT", "SHIELD KNIGHT", "WRAITH", "DOPPELGANGER"],
        3: ["KNIGHT", "SHIELD KNIGHT", "WRAITH", "WRAITH", "DREAD OGRE", "DREAD OGRE"],
        4: ["SPIDER", "SPIDER", "WRAITH", "DREAD OGRE", "DREAD OGRE", "DREAD OGRE", "ARCH-WARLOCK"],
    }

    roster = rosters.get(level.level_num, rosters[0])
    monsters = []
    used_cells = set()

    # Place one Spider near spawn on Level 1 for immediate action
    if level.level_num == 0:
        sx, sy = level.spawn_pos
        test_pos = None
        for dist in range(1, 5):
            if level.is_open(sx, sy - dist) and level.grid[sy - dist + 1][sx][0] != 3:
                test_pos = (sx, sy - dist)
            else:
                break
        if test_pos and test_pos != (sx, sy):
            monsters.append(Monster("SPIDER", test_pos[0], test_pos[1]))
            used_cells.add(test_pos)

    for m_name in roster:
        pos = rng.choice(open_coords)
        if pos not in used_cells:
            used_cells.add(pos)
            m = Monster(m_name, pos[0], pos[1])
            # Final Arch-Warlock carries the Crown Ring needed to finish the quest
            if m_name == "ARCH-WARLOCK":
                m.held_items.append(
                    GameItem("CROWN", "RING", revealed=False, reveal_req=140, swing_exertion=10.0, damage=0, is_magical=True, incant_word="AETHER", charges=1)
                )
            monsters.append(m)

    return monsters