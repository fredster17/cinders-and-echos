import random

# Wall states
OPEN = 0
WALL = 1
DOOR = 2
MAGIC = 3

# Directions: 0=North, 1=East, 2=South, 3=West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
DIR_NAMES = ["NORTH", "EAST", "SOUTH", "WEST"]

# Level generation seeds (5 distinct 32x32 dungeon floors)
LEVEL_SEEDS = [104729, 224737, 350377, 479909, 611953]


class DungeonLevel:
    def __init__(self, level_num=0, size=32):
        self.level_num = level_num
        self.size = size
        # Each cell stores [North, East, South, West] wall states
        self.grid = [[[WALL, WALL, WALL, WALL] for _ in range(size)] for _ in range(size)]
        self.visited = [[False for _ in range(size)] for _ in range(size)]
        self.spawn_pos = (16, 16)
        # Vertical features: (x, y) -> {"down": "HOLE"|"LADDER"|None, "up": "HOLE"|"LADDER"|None}
        self.verticals = {}
        self._generate()

    def is_open(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.visited[y][x]
        return False

    def _carve(self, x, y, direction):
        dx, dy = DIRS[direction]
        nx, ny = x + dx, y + dy
        opp = (direction + 2) % 4
        # 15% chance for standard doorway, 8% chance for hidden arcane wall
        roll = random.random()
        passage_type = DOOR if roll < 0.15 else (MAGIC if roll < 0.23 else OPEN)
        self.grid[y][x][direction] = passage_type
        self.grid[ny][nx][opp] = passage_type

    def _generate(self):
        rng = random.Random(LEVEL_SEEDS[self.level_num % len(LEVEL_SEEDS)])
        sx, sy = 16, 16
        self.spawn_pos = (sx, sy)
        self.visited[sy][sx] = True
        stack = [(sx, sy)]

        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for d, (dx, dy) in enumerate(DIRS):
                nx, ny = cx + dx, cy + dy
                if 1 <= nx < self.size - 1 and 1 <= ny < self.size - 1 and not self.visited[ny][nx]:
                    neighbors.append((d, nx, ny))

            if neighbors:
                d, nx, ny = rng.choice(neighbors)
                self.visited[ny][nx] = True
                # Carve using local rng for deterministic layouts
                opp = (d + 2) % 4
                roll = rng.random()
                passage_type = DOOR if roll < 0.15 else (MAGIC if roll < 0.23 else OPEN)
                self.grid[cy][cx][d] = passage_type
                self.grid[ny][nx][opp] = passage_type
                stack.append((nx, ny))
            else:
                stack.pop()

        # Add extra loops so creatures and players can flank
        open_cells = [(x, y) for y in range(2, self.size - 2) for x in range(2, self.size - 2) if self.visited[y][x]]
        for _ in range(38):
            cx, cy = rng.choice(open_cells)
            d = rng.randint(0, 3)
            dx, dy = DIRS[d]
            nx, ny = cx + dx, cy + dy
            if self.visited[ny][nx] and self.grid[cy][cx][d] == WALL:
                opp = (d + 2) % 4
                self.grid[cy][cx][d] = OPEN
                self.grid[ny][nx][opp] = OPEN

        # Place deterministic vertical shafts (holes & ladders) between floors
        # Guaranteed easy-to-find ladder/hole near spawn on each floor + 2 deeper shafts
        near_candidates = [
            (x, y) for (x, y) in open_cells
            if 3 <= abs(x - sx) + abs(y - sy) <= 7
        ]
        far_candidates = [
            (x, y) for (x, y) in open_cells
            if abs(x - sx) + abs(y - sy) > 9
        ]

        # Downward shafts (Levels 1-4 -> index 0..3)
        if self.level_num < 4:
            p1 = rng.choice(near_candidates) if near_candidates else open_cells[0]
            self.verticals[p1] = {"down": "LADDER", "up": None}
            for _ in range(2):
                p_deep = rng.choice(far_candidates)
                if p_deep not in self.verticals:
                    self.verticals[p_deep] = {"down": "HOLE", "up": None}

        # Upward shafts (Levels 2-5 -> index 1..4)
        if self.level_num > 0:
            # Place a return ladder right at spawn_pos or 1 step away so climbing back is always possible
            up_pos = (sx, sy)
            entry = self.verticals.setdefault(up_pos, {"down": None, "up": None})
            entry["up"] = "LADDER"
            p_ceil = rng.choice(far_candidates)
            if p_ceil not in self.verticals:
                self.verticals[p_ceil] = {"down": None, "up": "HOLE"}