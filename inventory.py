import random

CLASS_WEIGHTS = {
    "FLASK": 5,
    "RING": 1,
    "SCROLL": 10,
    "SHIELD": 25,
    "SWORD": 25,
    "TORCH": 10,
}

UNREVEALED_BASE = {
    "TORCH": "PINE",
    "SWORD": "WOODEN",
    "SHIELD": "LEATHER",
    "RING": "GOLD",
}


class GameItem:
    def __init__(
        self, proper_name, item_class, revealed=False, reveal_req=5,
        torch_range=0, magic_light=False, minutes_left=0,
        swing_exertion=6.0, damage=8, is_magical=False,
        phys_block=0.0, mag_block=0.0, incant_word=None, charges=0
    ):
        self.proper_name = proper_name
        self.item_class = item_class
        self.revealed = revealed
        self.reveal_req = reveal_req
        self.torch_range = torch_range
        self.magic_light = magic_light
        self.minutes_left = minutes_left
        self.swing_exertion = swing_exertion
        self.damage = damage
        self.is_magical = is_magical
        self.phys_block = phys_block
        self.mag_block = mag_block
        self.incant_word = incant_word
        self.charges = charges
        self.incanted = False
        self.is_lit = False

    @property
    def weight(self):
        return CLASS_WEIGHTS.get(self.item_class, 5)

    @property
    def display_name(self):
        if self.proper_name == "DEAD" and self.item_class == "TORCH":
            return "DEAD TORCH"
        if self.revealed:
            if self.item_class == "RING" and self.incanted and self.charges > 0:
                return f"{self.proper_name} RING ({self.charges})"
            return f"{self.proper_name} {self.item_class}"
        base = UNREVEALED_BASE.get(self.item_class)
        return f"{base} {self.item_class}" if base else self.item_class

    def matches_query(self, query_tokens):
        q = " ".join(query_tokens).upper()
        vis = self.display_name.upper()
        cls = self.item_class.upper()
        if vis.startswith(q) or cls.startswith(q):
            return True
        if len(query_tokens) >= 2:
            parts = vis.split()
            if len(parts) >= 2 and parts[0].startswith(query_tokens[0]) and parts[1].startswith(query_tokens[1]):
                return True
        return False

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["proper_name"], data["item_class"])
        obj.__dict__.update(data)
        return obj


def spawn_level_loot(level):
    """Distributes level-appropriate gear, rings, shields, flasks, and scrolls."""
    lvl = level.level_num
    open_coords = [(x, y) for y in range(level.size) for x in range(level.size) if level.is_open(x, y)]
    rng = random.Random(lvl + 42)
    floor_items = {}

    # Floor-specific progression items
    level_loot_pools = {
        0: [
            GameItem("LUNAR", "TORCH", revealed=False, reveal_req=25, torch_range=8, magic_light=True, minutes_left=30, damage=4),
            GameItem("IRON", "SWORD", revealed=False, reveal_req=13, swing_exertion=16.0, damage=22),
            GameItem("LEATHER", "SHIELD", revealed=True, reveal_req=5, swing_exertion=10.0, damage=10, phys_block=0.25, mag_block=0.05),
            GameItem("EMBER", "RING", revealed=False, reveal_req=35, swing_exertion=26.0, damage=65, is_magical=True, incant_word="IGNIS", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("THEWS", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("VISION", "SCROLL", revealed=False, reveal_req=50, damage=2),
        ],
        1: [
            GameItem("LUNAR", "TORCH", revealed=False, reveal_req=25, torch_range=8, magic_light=True, minutes_left=30, damage=4),
            GameItem("BRONZE", "SHIELD", revealed=False, reveal_req=30, swing_exertion=14.0, damage=15, phys_block=0.45, mag_block=0.15),
            GameItem("FROST", "RING", revealed=False, reveal_req=55, swing_exertion=30.0, damage=85, is_magical=True, incant_word="GLACIES", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("THEWS", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("ABYE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("SEER", "SCROLL", revealed=False, reveal_req=80, damage=2),
        ],
        2: [
            GameItem("SOLAR", "TORCH", revealed=False, reveal_req=70, torch_range=9, magic_light=True, minutes_left=60, damage=4),
            GameItem("ELVISH", "SWORD", revealed=False, reveal_req=60, swing_exertion=24.0, damage=48, is_magical=True),
            GameItem("EMBER", "RING", revealed=False, reveal_req=35, swing_exertion=26.0, damage=65, is_magical=True, incant_word="IGNIS", charges=3),
            GameItem("FROST", "RING", revealed=False, reveal_req=55, swing_exertion=30.0, damage=85, is_magical=True, incant_word="GLACIES", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("THEWS", "FLASK", revealed=False, reveal_req=40, damage=2),
        ],
        3: [
            GameItem("SOLAR", "TORCH", revealed=False, reveal_req=70, torch_range=9, magic_light=True, minutes_left=60, damage=4),
            GameItem("ELVISH", "SWORD", revealed=False, reveal_req=60, swing_exertion=24.0, damage=48, is_magical=True),
            GameItem("RUNE", "SHIELD", revealed=False, reveal_req=90, swing_exertion=16.0, damage=20, phys_block=0.65, mag_block=0.55),
            GameItem("STORM", "RING", revealed=False, reveal_req=110, swing_exertion=36.0, damage=125, is_magical=True, incant_word="FULGUR", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("THEWS", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("SEER", "SCROLL", revealed=False, reveal_req=80, damage=2),
        ],
        4: [
            GameItem("SOLAR", "TORCH", revealed=False, reveal_req=70, torch_range=9, magic_light=True, minutes_left=60, damage=4),
            GameItem("RUNE", "SHIELD", revealed=False, reveal_req=90, swing_exertion=16.0, damage=20, phys_block=0.65, mag_block=0.55),
            GameItem("STORM", "RING", revealed=False, reveal_req=110, swing_exertion=36.0, damage=125, is_magical=True, incant_word="FULGUR", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("THEWS", "FLASK", revealed=False, reveal_req=40, damage=2),
        ],
    }

    # Starter stash on Level 1 so you can immediately test rings, shields, scrolls & flasks
    if lvl == 0:
        sx, sy = level.spawn_pos
        floor_items[(sx, sy)] = [
            GameItem("LUNAR", "TORCH", revealed=False, reveal_req=25, torch_range=8, magic_light=True, minutes_left=30, damage=4),
            GameItem("LEATHER", "SHIELD", revealed=True, reveal_req=5, swing_exertion=10.0, damage=10, phys_block=0.25, mag_block=0.05),
            GameItem("EMBER", "RING", revealed=False, reveal_req=35, swing_exertion=26.0, damage=65, is_magical=True, incant_word="IGNIS", charges=3),
            GameItem("HALE", "FLASK", revealed=False, reveal_req=40, damage=2),
            GameItem("VISION", "SCROLL", revealed=False, reveal_req=50, damage=2),
        ]

    for item in level_loot_pools.get(lvl, []):
        pos = rng.choice(open_coords)
        floor_items.setdefault(pos, []).append(item)

    return floor_items