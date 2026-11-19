import pygame
import random
import math
from maze import DIRS, OPEN, DOOR, MAGIC

BLACK = (0, 0, 0)
GREEN = (0, 255, 100)
DIM_GREEN = (0, 120, 45)
AMBER = (255, 180, 0)
RED = (255, 50, 50)
GOLD = (230, 195, 110)
CYAN = (90, 220, 255)

ZOOM_FACTORS = [1.0, 0.64, 0.40, 0.25, 0.155, 0.10, 0.06, 0.04, 0.02]


def generate_stone_texture(size=128):
    surf = pygame.Surface((size, size))
    surf.fill((38, 40, 44))
    rng = random.Random(1982)

    rows = 6
    row_h = size // rows
    for r in range(rows):
        y = r * row_h
        offset = (size // 4) if (r % 2 == 1) else 0
        cols = 3
        col_w = size // cols
        for c in range(-1, cols + 1):
            x = c * col_w + offset
            shade = rng.randint(68, 102)
            tint_r = shade + rng.randint(-4, 6)
            tint_g = shade + rng.randint(-2, 6)
            tint_b = shade + rng.randint(0, 10)
            brick_rect = pygame.Rect(x + 2, y + 2, col_w - 4, row_h - 4)
            pygame.draw.rect(surf, (tint_r, tint_g, tint_b), brick_rect)
            pygame.draw.line(surf, (tint_r + 18, tint_g + 18, tint_b + 18), (brick_rect.left, brick_rect.top), (brick_rect.right - 1, brick_rect.top))
            pygame.draw.line(surf, (tint_r - 22, tint_g - 22, tint_b - 22), (brick_rect.left, brick_rect.bottom - 1), (brick_rect.right - 1, brick_rect.bottom - 1))

    for _ in range(450):
        px, py = rng.randint(0, size - 1), rng.randint(0, size - 1)
        delta = rng.choice([-14, 12])
        c = surf.get_at((px, py))
        surf.set_at((px, py), (max(0, min(255, c.r + delta)), max(0, min(255, c.g + delta)), max(0, min(255, c.b + delta))))

    return surf


def generate_door_texture(size=128):
    surf = pygame.Surface((size, size))
    surf.fill((78, 48, 26))
    rng = random.Random(82)
    for p in range(4):
        px = p * (size // 4)
        shade = rng.randint(-8, 10)
        pygame.draw.rect(surf, (78 + shade, 48 + shade, 26 + shade // 2), (px + 1, 0, size // 4 - 2, size))
    for by in (int(size * 0.22), int(size * 0.78)):
        pygame.draw.rect(surf, (45, 48, 54), (0, by - 5, size, 10))
        for rx in range(12, size, 24):
            pygame.draw.circle(surf, (110, 115, 125), (rx, by), 2)
    pygame.draw.circle(surf, (130, 135, 145), (int(size * 0.72), int(size * 0.54)), 8, 2)
    return surf


class HDRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.stone_tex = generate_stone_texture(128)
        self.door_tex = generate_door_texture(128)
        self.flicker_phase = 0.0

    def get_view_rect(self, depth):
        cx, cy = self.width // 2, 245
        half_w = 340 * ZOOM_FACTORS[depth]
        half_h = 200 * ZOOM_FACTORS[depth]
        return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def _tint_surface(self, surf, light_rgb):
        tinted = surf.copy()
        tinted.fill(light_rgb, special_flags=pygame.BLEND_MULT)
        return tinted

    def draw_textured_side_wall(self, x_near, y_near_top, y_near_bot, x_far, y_far_top, y_far_bot, light_rgb, has_door=False, has_magic=False):
        dx = x_far - x_near
        steps = int(abs(dx))
        if steps <= 0:
            return

        tex = self._tint_surface(self.stone_tex, light_rgb)
        door_tex = self._tint_surface(self.door_tex, light_rgb) if has_door else None
        tex_w, tex_h = tex.get_size()

        step_dir = 1 if dx > 0 else -1
        stride = 2 if steps > 20 else 1

        for i in range(0, steps, stride):
            t = i / float(steps)
            cur_x = int(x_near + i * step_dir)
            top_y = int(y_near_top + (y_far_top - y_near_top) * t)
            bot_y = int(y_near_bot + (y_far_bot - y_near_bot) * t)
            col_h = max(1, bot_y - top_y)

            u = int(t * (tex_w - 1))
            in_door = has_door and (0.25 <= t <= 0.75)
            if in_door:
                door_top = int(top_y + col_h * 0.22)
                wall_cap_h = max(1, door_top - top_y)
                cap_strip = pygame.transform.scale(tex.subsurface((u, 0, 1, int(tex_h * 0.22))), (stride, wall_cap_h))
                self.screen.blit(cap_strip, (cur_x, top_y))
                du = int(((t - 0.25) / 0.5) * (tex_w - 1))
                door_strip = pygame.transform.scale(door_tex.subsurface((du, 0, 1, tex_h)), (stride, max(1, bot_y - door_top)))
                self.screen.blit(door_strip, (cur_x, door_top))
            else:
                strip = pygame.transform.scale(tex.subsurface((u, 0, 1, tex_h)), (stride, col_h))
                self.screen.blit(strip, (cur_x, top_y))

        if has_magic:
            dl = x_near + (x_far - x_near) * 0.25
            dr = x_near + (x_far - x_near) * 0.75
            mid_x = (dl + dr) / 2
            dt_mid = ((y_near_top + y_far_top) / 2) + (((y_near_bot + y_far_bot) / 2) - ((y_near_top + y_far_top) / 2)) * 0.25
            db_l = y_near_bot + (y_far_bot - y_near_bot) * 0.25
            db_r = y_near_bot + (y_far_bot - y_near_bot) * 0.75
            pygame.draw.polygon(self.screen, CYAN, [(dl, db_l), (mid_x, dt_mid), (dr, db_r)], 2)

    def draw_textured_front_wall(self, fl, ft, fr, fb, light_rgb, has_door=False, has_magic=False):
        w = max(1, int(fr - fl))
        h = max(1, int(fb - ft))
        wall_surf = pygame.transform.scale(self._tint_surface(self.stone_tex, light_rgb), (w, h))
        self.screen.blit(wall_surf, (int(fl), int(ft)))
        border_col = (max(0, light_rgb[0] // 3), max(0, light_rgb[1] // 3), max(0, light_rgb[2] // 3))
        pygame.draw.rect(self.screen, border_col, (int(fl), int(ft), w, h), 1)

        if has_door:
            dw = max(2, int(w * 0.36))
            dh = max(2, int(h * 0.76))
            dx = int(fl + w * 0.32)
            dy = int(fb - dh)
            d_surf = pygame.transform.scale(self._tint_surface(self.door_tex, light_rgb), (dw, dh))
            self.screen.blit(d_surf, (dx, dy))
            pygame.draw.rect(self.screen, (20, 15, 10), (dx, dy, dw, dh), 2)
        elif has_magic:
            apex = ((fl + fr) / 2, ft + h * 0.25)
            pygame.draw.polygon(self.screen, CYAN, [(fl + w * 0.32, fb), apex, (fr - w * 0.32, fb)], 3)

    def draw_verticals(self, vert, near_rect, far_rect, atten):
        nl, nt, nr, nb = near_rect
        fl, ft, fr, fb = far_rect
        cx = (nl + nr) / 2
        pit_col = (int(12 * atten), int(10 * atten), int(8 * atten))
        rim_col = (int(140 * atten), int(125 * atten), int(95 * atten))
        wood_col = (int(165 * atten), int(115 * atten), int(65 * atten))

        if vert.get("down"):
            pts = [
                (nl + (nr - nl) * 0.32, nb - (nb - fb) * 0.2),
                (fl + (fr - fl) * 0.32, fb + (nb - fb) * 0.2),
                (fr - (fr - fl) * 0.32, fb + (nb - fb) * 0.2),
                (nr - (nr - nl) * 0.32, nb - (nb - fb) * 0.2),
            ]
            pygame.draw.polygon(self.screen, pit_col, pts)
            pygame.draw.polygon(self.screen, rim_col, pts, 2)

        if vert.get("up"):
            pts = [
                (nl + (nr - nl) * 0.32, nt + (ft - nt) * 0.2),
                (fl + (fr - fl) * 0.32, ft - (ft - nt) * 0.2),
                (fr - (fr - fl) * 0.32, ft - (ft - nt) * 0.2),
                (nr - (nr - nl) * 0.32, nt + (ft - nt) * 0.2),
            ]
            pygame.draw.polygon(self.screen, pit_col, pts)
            pygame.draw.polygon(self.screen, rim_col, pts, 2)

        if vert.get("down") == "LADDER" or vert.get("up") == "LADDER":
            top_y = ft if vert.get("up") == "LADDER" else (ft + fb) * 0.45
            bot_y = fb if vert.get("down") == "LADDER" else (ft + fb) * 0.55
            rail_w = (fr - fl) * 0.14
            pygame.draw.line(self.screen, wood_col, (cx - rail_w, top_y), (cx - rail_w, bot_y), 3)
            pygame.draw.line(self.screen, wood_col, (cx + rail_w, top_y), (cx + rail_w, bot_y), 3)
            for r in range(1, 6):
                ry = top_y + (bot_y - top_y) * (r / 6.0)
                pygame.draw.line(self.screen, wood_col, (cx - rail_w, ry), (cx + rail_w, ry), 2)

    def draw_shaded_monster(self, monster, rect, brightness):
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) / 2
        w = x2 - x1
        h = y2 - y1
        bottom = y2 - h * 0.04
        b = max(0.15, min(1.0, brightness))

        def shade(rgb):
            return (int(rgb[0] * b), int(rgb[1] * b), int(rgb[2] * b))

        pygame.draw.ellipse(self.screen, shade((15, 12, 10)), (cx - w * 0.22, bottom - h * 0.04, w * 0.44, h * 0.07))

        if monster.shape == "SPIDER":
            body_y = bottom - h * 0.14
            r = max(4, int(w * 0.09))
            for side in (-1, 1):
                for leg in range(3):
                    spread = (0.15 + leg * 0.07) * w * side
                    knee_y = body_y - h * (0.09 - leg * 0.02)
                    pygame.draw.line(self.screen, shade((55, 45, 50)), (cx, body_y), (cx + spread * 0.6, knee_y), max(2, int(w * 0.015)))
                    pygame.draw.line(self.screen, shade((40, 32, 36)), (cx + spread * 0.6, knee_y), (cx + spread, bottom), max(2, int(w * 0.012)))
            pygame.draw.circle(self.screen, shade((70, 30, 40)), (int(cx), int(body_y)), r)
            pygame.draw.circle(self.screen, shade((255, 40, 40)), (int(cx - r * 0.35), int(body_y - r * 0.2)), max(1, int(r * 0.2)))
            pygame.draw.circle(self.screen, shade((255, 40, 40)), (int(cx + r * 0.35), int(body_y - r * 0.2)), max(1, int(r * 0.2)))

        elif monster.shape == "SNAKE":
            pts = [
                (cx - w * 0.14, bottom),
                (cx + w * 0.12, bottom - h * 0.12),
                (cx - w * 0.10, bottom - h * 0.26),
                (cx + w * 0.06, bottom - h * 0.40),
                (cx - w * 0.03, bottom - h * 0.44),
            ]
            pygame.draw.lines(self.screen, shade((45, 145, 65)), False, pts, max(3, int(w * 0.035)))
            pygame.draw.circle(self.screen, shade((255, 210, 40)), (int(cx - w * 0.03), int(bottom - h * 0.44)), max(2, int(w * 0.015)))

        elif monster.shape == "BLOB":
            top_y = bottom - h * 0.44
            blob_rect = (cx - w * 0.23, top_y, w * 0.46, h * 0.44)
            pygame.draw.ellipse(self.screen, shade((40, 175, 110)), blob_rect)
            pygame.draw.ellipse(self.screen, shade((110, 235, 165)), (cx - w * 0.16, top_y + h * 0.05, w * 0.25, h * 0.20))
            eye_y = int(top_y + h * 0.15)
            pygame.draw.circle(self.screen, shade((10, 30, 20)), (int(cx - w * 0.07), eye_y), max(2, int(w * 0.025)))
            pygame.draw.circle(self.screen, shade((10, 30, 20)), (int(cx + w * 0.07), eye_y), max(2, int(w * 0.025)))

        elif monster.shape in ("GIANT", "KNIGHT"):
            top_y = bottom - h * 0.72
            bw = w * 0.28
            armor_col = (130, 138, 150) if monster.shape == "KNIGHT" else (125, 108, 92)
            pygame.draw.rect(self.screen, shade(armor_col), (cx - bw * 0.38, top_y + h * 0.48, bw * 0.28, h * 0.24))
            pygame.draw.rect(self.screen, shade(armor_col), (cx + bw * 0.10, top_y + h * 0.48, bw * 0.28, h * 0.24))
            pygame.draw.rect(self.screen, shade(armor_col), (cx - bw / 2, top_y + h * 0.14, bw, h * 0.36))
            pygame.draw.circle(self.screen, shade(armor_col), (int(cx), int(top_y + h * 0.07)), max(3, int(w * 0.075)))
            pygame.draw.line(self.screen, shade((255, 80, 40)), (cx - w * 0.04, top_y + h * 0.07), (cx + w * 0.04, top_y + h * 0.07), max(2, int(h * 0.015)))
            pygame.draw.line(self.screen, shade((190, 200, 215)), (cx + bw / 2, top_y + h * 0.24), (cx + bw * 1.15, top_y + h * 0.02), max(2, int(w * 0.02)))

        else:
            top_y = bottom - h * 0.76
            cloak_col = (95, 160, 255) if monster.shape == "WRAITH" else (180, 75, 235)
            robe = [(cx, top_y), (cx - w * 0.23, bottom), (cx + w * 0.23, bottom)]
            pygame.draw.polygon(self.screen, shade(cloak_col), robe)
            pygame.draw.circle(self.screen, shade((255, 240, 120)), (int(cx - w * 0.03), int(top_y + h * 0.14)), max(2, int(w * 0.015)))
            pygame.draw.circle(self.screen, shade((255, 240, 120)), (int(cx + w * 0.03), int(top_y + h * 0.14)), max(2, int(w * 0.015)))

    def render_corridor(self, level, px, py, pdir, active_torch, floor_items, monsters):
        vp = pygame.Rect(60, 45, 680, 400)
        self.screen.set_clip(vp)

        if active_torch is None or not active_torch.is_lit or active_torch.torch_range <= 0:
            msg = self.small_font.render("IT IS PITCH DARK. (PULL A TORCH AND USE IT)", True, DIM_GREEN)
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 235))
            self.screen.set_clip(None)
            return

        flicker = 0.92 + 0.08 * math.sin(self.flicker_phase * 11.0) * math.cos(self.flicker_phase * 7.3)
        if active_torch.minutes_left <= 5:
            flicker *= 0.55

        base_light = (195, 225, 255) if active_torch.magic_light else (255, 195, 125)

        for i in range(20):
            t = i / 20.0
            shade = int((1.0 - t) * 48 * flicker)
            ceil_col = (int(shade * 0.7), int(shade * 0.75), int(shade * 0.9))
            floor_col = (int(shade * 0.95), int(shade * 0.85), int(shade * 0.7))
            strip_h = 10
            pygame.draw.rect(self.screen, ceil_col, (60, 45 + i * strip_h, 680, strip_h))
            pygame.draw.rect(self.screen, floor_col, (60, 445 - (i + 1) * strip_h, 680, strip_h))

        slices = []
        cx, cy = px, py
        torch_range = active_torch.torch_range
        magic_light = active_torch.magic_light

        for depth in range(min(torch_range, len(ZOOM_FACTORS) - 1)):
            if not level.is_open(cx, cy):
                break
            cell = level.grid[cy][cx]
            slices.append((depth, cx, cy, cell))
            if cell[pdir] != OPEN:
                break
            dx, dy = DIRS[pdir]
            cx += dx
            cy += dy

        left_dir = (pdir - 1) % 4
        right_dir = (pdir + 1) % 4

        for depth, cx, cy, cell in reversed(slices):
            atten = max(0.12, ((torch_range - depth) / float(torch_range)) ** 1.35) * flicker
            light_rgb = (
                int(min(255, base_light[0] * atten)),
                int(min(255, base_light[1] * atten)),
                int(min(255, base_light[2] * atten)),
            )

            nl, nt, nr, nb = self.get_view_rect(depth)
            fl, ft, fr, fb = self.get_view_rect(depth + 1)
            front_wall, left_wall, right_wall = cell[pdir], cell[left_dir], cell[right_dir]

            if front_wall != OPEN:
                self.draw_textured_front_wall(
                    fl, ft, fr, fb, light_rgb,
                    has_door=(front_wall == DOOR),
                    has_magic=(front_wall == MAGIC and magic_light)
                )

            if left_wall == OPEN:
                rec_w = max(4, int(fl - nl))
                rec_h = max(4, int(fb - ft))
                dark_rgb = (light_rgb[0] // 2, light_rgb[1] // 2, light_rgb[2] // 2)
                recess_surf = pygame.transform.scale(self._tint_surface(self.stone_tex, dark_rgb), (rec_w, rec_h))
                self.screen.blit(recess_surf, (int(nl), int(ft)))
            else:
                self.draw_textured_side_wall(
                    nl, nt, nb, fl, ft, fb, light_rgb,
                    has_door=(left_wall == DOOR),
                    has_magic=(left_wall == MAGIC and magic_light)
                )

            if right_wall == OPEN:
                rec_w = max(4, int(nr - fr))
                rec_h = max(4, int(fb - ft))
                dark_rgb = (light_rgb[0] // 2, light_rgb[1] // 2, light_rgb[2] // 2)
                recess_surf = pygame.transform.scale(self._tint_surface(self.stone_tex, dark_rgb), (rec_w, rec_h))
                self.screen.blit(recess_surf, (int(fr), int(ft)))
            else:
                self.draw_textured_side_wall(
                    nr, nt, nb, fr, ft, fb, light_rgb,
                    has_door=(right_wall == DOOR),
                    has_magic=(right_wall == MAGIC and magic_light)
                )

            if (cx, cy) in level.verticals:
                self.draw_verticals(level.verticals[(cx, cy)], (nl, nt, nr, nb), (fl, ft, fr, fb), atten)

            if floor_items.get((cx, cy)):
                item_w = max(6, int((fr - fl) * 0.22))
                item_h = max(3, int((fb - ft) * 0.06))
                ix = int((fl + fr) / 2 - item_w / 2)
                iy = int(fb - item_h - 4)
                glint_col = (int(GOLD[0] * atten), int(GOLD[1] * atten), int(GOLD[2] * atten))
                pygame.draw.rect(self.screen, glint_col, (ix, iy, item_w, item_h))

            for m in monsters:
                if m.alive and (m.x, m.y) == (cx, cy):
                    if not m.is_magical or magic_light:
                        draw_box = (nl, nt, nr, nb) if depth == 0 else (fl, ft, fr, fb)
                        self.draw_shaded_monster(m, draw_box, atten)

        self.screen.set_clip(None)

    def render_examine(self, room_items, backpack, active_torch, room_monsters, vert):
        self.screen.blit(self.font.render("IN THIS ROOM", True, GOLD), (315, 65))
        lines = [item.display_name for item in room_items]
        for m in room_monsters:
            lines.insert(0, f"!! {m.name} !!")
        if vert:
            if vert.get("down"):
                lines.append(f"[SHAFT DOWN: {vert['down']}]")
            if vert.get("up"):
                lines.append(f"[SHAFT UP: {vert['up']}]")

        if not lines:
            self.screen.blit(self.small_font.render("(NOTHING ON FLOOR)", True, (130, 120, 100)), (90, 100))
        else:
            for idx, label in enumerate(lines):
                col = 90 if idx % 2 == 0 else 420
                row = 100 + (idx // 2) * 24
                c = RED if label.startswith("!!") else (CYAN if label.startswith("[") else GOLD)
                txt_surf = self.small_font.render(label, True, c)
                self.screen.blit(txt_surf, (col, row))

        pygame.draw.line(self.screen, GOLD, (75, 225), (725, 225), 2)
        self.screen.blit(self.font.render("BACKPACK", True, GOLD), (340, 240))

        if not backpack:
            self.screen.blit(self.small_font.render("(EMPTY)", True, (130, 120, 100)), (90, 280))
        else:
            for idx, item in enumerate(backpack):
                col = 90 if idx % 2 == 0 else 420
                row = 280 + (idx // 2) * 24
                if item is active_torch and item.is_lit:
                    pygame.draw.rect(self.screen, AMBER, (col - 4, row - 2, 240, 20))
                    txt = self.small_font.render(item.display_name, True, BLACK)
                else:
                    txt = self.small_font.render(item.display_name, True, GOLD)
                self.screen.blit(txt, (col, row))

        hint = self.small_font.render("PRESS TAB OR TYPE 'LOOK' TO RETURN", True, (150, 140, 115))
        self.screen.blit(hint, (235, 415))

    def render_map(self, level, px, py, monsters, show_verticals=False):
        cell_px = 11
        ox = (self.width - 32 * cell_px) // 2
        oy = 65
        for y in range(32):
            for x in range(32):
                rect = (ox + x * cell_px, oy + y * cell_px, cell_px, cell_px)
                if level.is_open(x, y):
                    pygame.draw.rect(self.screen, (95, 80, 55), rect)
                else:
                    pygame.draw.rect(self.screen, (40, 34, 24), rect, 1)

        if show_verticals:
            for (vx, vy), info in level.verticals.items():
                vcx = ox + vx * cell_px + cell_px // 2
                vcy = oy + vy * cell_px + cell_px // 2
                col = CYAN if (info.get("down") == "LADDER" or info.get("up") == "LADDER") else GOLD
                pygame.draw.rect(self.screen, col, (vcx - 3, vcy - 3, 6, 6))

        for m in monsters:
            if m.alive:
                mcx = ox + m.x * cell_px + cell_px // 2
                mcy = oy + m.y * cell_px + cell_px // 2
                pygame.draw.circle(self.screen, RED, (mcx, mcy), 3)

        pcx = ox + px * cell_px + cell_px // 2
        pcy = oy + py * cell_px + cell_px // 2
        pygame.draw.circle(self.screen, AMBER, (pcx, pcy), 4)

    def render_frame(self, state):
        self.flicker_phase += 0.016
        vitals = state["vitals"]
        self.screen.fill((12, 11, 10))
        pygame.draw.rect(self.screen, (90, 80, 65), (58, 43, 684, 404), 2)

        if state.get("victory"):
            msg = self.font.render("THE CROWN OF AETHER SHINES - VICTORY!", True, CYAN)
            sub = self.small_font.render("YOU HAVE CONQUERED THE DEPTHS OF CINDERS & ECHO!", True, GOLD)
            sub2 = self.small_font.render("TYPE 'RESTART' TO PLAY AGAIN", True, (150, 140, 115))
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 195))
            self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, 235))
            self.screen.blit(sub2, (self.width // 2 - sub2.get_width() // 2, 275))
        elif vitals.dead:
            msg = self.font.render("YOUR HEART HAS STOPPED - GAME OVER", True, RED)
            sub = self.small_font.render("TYPE 'RESTART' TO TRY AGAIN", True, GOLD)
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))
            self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, 255))
        elif vitals.fainted:
            msg = self.font.render("YOU HAVE FAINTED FROM EXHAUSTION...", True, AMBER)
            sub = self.small_font.render("RESTING UNTIL YOUR HEART RATE RECOVERS...", True, (150, 140, 115))
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))
            self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, 255))
        else:
            mode = state["view_mode"]
            if mode == "EXAMINE":
                room_items = state["floor_items"].get((state["px"], state["py"]), [])
                room_monsters = [m for m in state["monsters"] if m.alive and (m.x, m.y) == (state["px"], state["py"])]
                vert = state["level"].verticals.get((state["px"], state["py"]))
                self.render_examine(room_items, state["backpack"], state["active_torch"], room_monsters, vert)
            elif mode in ("MAP", "VISION_MAP"):
                self.render_map(state["level"], state["px"], state["py"], state["monsters"], show_verticals=(mode == "VISION_MAP"))
            else:
                self.render_corridor(
                    state["level"], state["px"], state["py"], state["pdir"],
                    state["active_torch"], state["floor_items"], state["monsters"]
                )

        left_txt = state["left_hand"].display_name if state["left_hand"] else "EMPTY"
        right_txt = state["right_hand"].display_name if state["right_hand"] else "EMPTY"
        right_surf = self.small_font.render(right_txt, True, GOLD)

        self.screen.blit(self.small_font.render(left_txt, True, GOLD), (60, 460))
        self.screen.blit(right_surf, (740 - right_surf.get_width(), 460))

        if vitals.dead:
            pygame.draw.line(self.screen, RED, (self.width // 2 - 18, 468), (self.width // 2 + 18, 468), 2)
        else:
            heart_color = AMBER
            if vitals.current_bpm >= vitals.faint_threshold - 20:
                heart_color = RED
            elif vitals.current_bpm >= 115:
                heart_color = (255, 110, 40)
            heart_r = int(9 + 6 * state["pulse"])
            pygame.draw.circle(self.screen, heart_color, (self.width // 2, 468), heart_r, 2)

        self.screen.blit(self.small_font.render(state["status"], True, GOLD), (60, 505))
        prompt_text = "> [UNCONSCIOUS]" if (vitals.fainted and not vitals.dead) else f"> {state['cmd_buffer']}_"
        self.screen.blit(self.font.render(prompt_text, True, GOLD), (60, 535))
        pygame.display.flip()