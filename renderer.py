import pygame
from maze import DIRS, OPEN, DOOR, MAGIC

BLACK = (0, 0, 0)
GREEN = (0, 255, 100)
DIM_GREEN = (0, 120, 45)
AMBER = (255, 180, 0)
RED = (255, 50, 50)
CYAN = (90, 220, 255)

ZOOM_FACTORS = [1.0, 0.64, 0.40, 0.25, 0.155, 0.10, 0.06, 0.04, 0.02]


class WireframeRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 16)

    def get_view_rect(self, depth):
        cx, cy = self.width // 2, 245
        half_w = 340 * ZOOM_FACTORS[depth]
        half_h = 200 * ZOOM_FACTORS[depth]
        return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def draw_door_frame(self, x1, y1, x2, y2, is_side=False, color=GREEN):
        if not is_side:
            w, h = x2 - x1, y2 - y1
            pygame.draw.rect(self.screen, color, (x1 + w * 0.32, y1 + h * 0.25, w * 0.36, h * 0.75), 2)
        else:
            dl = x1 + (x2 - x1) * 0.25
            dr = x1 + (x2 - x1) * 0.75
            dt_l = y1[0] + (y2[0] - y1[0]) * 0.25
            dt_r = y1[0] + (y2[0] - y1[0]) * 0.75
            db_l = y1[1] + (y2[1] - y1[1]) * 0.25
            db_r = y1[1] + (y2[1] - y1[1]) * 0.75
            dt_l += (db_l - dt_l) * 0.25
            dt_r += (db_r - dt_r) * 0.25
            pygame.draw.polygon(self.screen, color, [(dl, db_l), (dl, dt_l), (dr, dt_r), (dr, db_r)], 2)

    def draw_magic_triangle(self, x1, y1, x2, y2, is_side=False, color=GREEN):
        if not is_side:
            w, h = x2 - x1, y2 - y1
            apex = ((x1 + x2) / 2, y1 + h * 0.25)
            pygame.draw.polygon(self.screen, color, [(x1 + w * 0.32, y2), apex, (x2 - w * 0.32, y2)], 2)
        else:
            dl = x1 + (x2 - x1) * 0.25
            dr = x1 + (x2 - x1) * 0.75
            mid_x = (dl + dr) / 2
            dt_mid = ((y1[0] + y2[0]) / 2) + (((y1[1] + y2[1]) / 2) - ((y1[0] + y2[0]) / 2)) * 0.25
            db_l = y1[1] + (y2[1] - y1[1]) * 0.25
            db_r = y1[1] + (y2[1] - y1[1]) * 0.75
            pygame.draw.polygon(self.screen, color, [(dl, db_l), (mid_x, dt_mid), (dr, db_r)], 2)

    def draw_verticals(self, vert, near_rect, far_rect, color):
        """Renders trapezoidal floor pits, ceiling hatches, and ladders."""
        nl, nt, nr, nb = near_rect
        fl, ft, fr, fb = far_rect
        cx = (nl + nr) / 2

        if vert.get("down"):
            pts = [
                (nl + (nr - nl) * 0.32, nb - (nb - fb) * 0.2),
                (fl + (fr - fl) * 0.32, fb + (nb - fb) * 0.2),
                (fr - (fr - fl) * 0.32, fb + (nb - fb) * 0.2),
                (nr - (nr - nl) * 0.32, nb - (nb - fb) * 0.2),
            ]
            pygame.draw.polygon(self.screen, color, pts, 2)

        if vert.get("up"):
            pts = [
                (nl + (nr - nl) * 0.32, nt + (ft - nt) * 0.2),
                (fl + (fr - fl) * 0.32, ft - (ft - nt) * 0.2),
                (fr - (fr - fl) * 0.32, ft - (ft - nt) * 0.2),
                (nr - (nr - nl) * 0.32, nt + (ft - nt) * 0.2),
            ]
            pygame.draw.polygon(self.screen, color, pts, 2)

        if vert.get("down") == "LADDER" or vert.get("up") == "LADDER":
            top_y = ft if vert.get("up") == "LADDER" else (ft + fb) * 0.45
            bot_y = fb if vert.get("down") == "LADDER" else (ft + fb) * 0.55
            rail_w = (fr - fl) * 0.14
            pygame.draw.line(self.screen, color, (cx - rail_w, top_y), (cx - rail_w, bot_y), 2)
            pygame.draw.line(self.screen, color, (cx + rail_w, top_y), (cx + rail_w, bot_y), 2)
            for r in range(1, 5):
                ry = top_y + (bot_y - top_y) * (r / 5.0)
                pygame.draw.line(self.screen, color, (cx - rail_w, ry), (cx + rail_w, ry), 1)

    def draw_monster_wireframe(self, monster, rect, color):
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) / 2
        w = x2 - x1
        h = y2 - y1
        bottom = y2 - h * 0.04

        if monster.shape == "SPIDER":
            body_y = bottom - h * 0.14
            r = max(3, int(w * 0.08))
            pygame.draw.circle(self.screen, color, (int(cx), int(body_y)), r, 2)
            for side in (-1, 1):
                for leg in range(3):
                    spread = (0.14 + leg * 0.07) * w * side
                    knee_y = body_y - h * (0.08 - leg * 0.02)
                    pygame.draw.line(self.screen, color, (cx, body_y), (cx + spread * 0.6, knee_y), 2)
                    pygame.draw.line(self.screen, color, (cx + spread * 0.6, knee_y), (cx + spread, bottom), 2)

        elif monster.shape == "SNAKE":
            pts = [
                (cx - w * 0.14, bottom),
                (cx + w * 0.12, bottom - h * 0.12),
                (cx - w * 0.10, bottom - h * 0.26),
                (cx + w * 0.06, bottom - h * 0.40),
                (cx - w * 0.03, bottom - h * 0.44),
            ]
            pygame.draw.lines(self.screen, color, False, pts, 2)

        elif monster.shape == "BLOB":
            top_y = bottom - h * 0.42
            pygame.draw.ellipse(self.screen, color, (cx - w * 0.22, top_y, w * 0.44, h * 0.42), 2)
            eye_y = int(top_y + h * 0.14)
            pygame.draw.circle(self.screen, color, (int(cx - w * 0.07), eye_y), max(2, int(w * 0.02)))
            pygame.draw.circle(self.screen, color, (int(cx + w * 0.07), eye_y), max(2, int(w * 0.02)))

        elif monster.shape in ("GIANT", "KNIGHT"):
            top_y = bottom - h * 0.72
            bw = w * 0.26
            pygame.draw.rect(self.screen, color, (cx - bw / 2, top_y + h * 0.14, bw, h * 0.36), 2)
            pygame.draw.circle(self.screen, color, (int(cx), int(top_y + h * 0.07)), max(3, int(w * 0.07)), 2)
            pygame.draw.line(self.screen, color, (cx - bw * 0.3, top_y + h * 0.50), (cx - bw * 0.4, bottom), 2)
            pygame.draw.line(self.screen, color, (cx + bw * 0.3, top_y + h * 0.50), (cx + bw * 0.4, bottom), 2)
            pygame.draw.line(self.screen, color, (cx + bw / 2, top_y + h * 0.22), (cx + bw * 1.1, top_y + h * 0.05), 2)

        else:
            top_y = bottom - h * 0.75
            robe = [(cx, top_y), (cx - w * 0.22, bottom), (cx + w * 0.22, bottom)]
            pygame.draw.polygon(self.screen, color, robe, 2)
            pygame.draw.circle(self.screen, color, (int(cx), int(top_y + h * 0.12)), max(2, int(w * 0.03)))

    def render_corridor(self, level, px, py, pdir, active_torch, floor_items, monsters):
        if active_torch is None or not active_torch.is_lit or active_torch.torch_range <= 0:
            msg = self.small_font.render("IT IS PITCH DARK. (PULL A TORCH AND USE IT)", True, DIM_GREEN)
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 235))
            return

        wall_color = DIM_GREEN if active_torch.minutes_left <= 5 else GREEN
        torch_range = active_torch.torch_range
        magic_light = active_torch.magic_light
        cx, cy = px, py
        left_dir = (pdir - 1) % 4
        right_dir = (pdir + 1) % 4

        for depth in range(min(torch_range, len(ZOOM_FACTORS) - 1)):
            if not level.is_open(cx, cy):
                break

            cell = level.grid[cy][cx]
            front_wall, left_wall, right_wall = cell[pdir], cell[left_dir], cell[right_dir]
            nl, nt, nr, nb = self.get_view_rect(depth)
            fl, ft, fr, fb = self.get_view_rect(depth + 1)

            if (cx, cy) in level.verticals:
                self.draw_verticals(level.verticals[(cx, cy)], (nl, nt, nr, nb), (fl, ft, fr, fb), wall_color)

            if floor_items.get((cx, cy)):
                item_w = (fr - fl) * 0.22
                item_h = (fb - ft) * 0.08
                ix = (fl + fr) / 2 - item_w / 2
                iy = fb - item_h - 4
                pygame.draw.rect(self.screen, wall_color, (ix, iy, item_w, item_h), 1)

            if left_wall == OPEN:
                pygame.draw.line(self.screen, wall_color, (nl, ft), (fl, ft), 2)
                pygame.draw.line(self.screen, wall_color, (nl, fb), (fl, fb), 2)
                pygame.draw.line(self.screen, wall_color, (fl, ft), (fl, fb), 2)
                pygame.draw.line(self.screen, wall_color, (nl, nt), (fl, ft), 2)
            else:
                pygame.draw.line(self.screen, wall_color, (nl, nt), (fl, ft), 2)
                pygame.draw.line(self.screen, wall_color, (nl, nb), (fl, fb), 2)
                pygame.draw.line(self.screen, wall_color, (fl, ft), (fl, fb), 2)
                if left_wall == DOOR:
                    self.draw_door_frame(nl, (nt, nb), fl, (ft, fb), is_side=True, color=wall_color)
                elif left_wall == MAGIC and magic_light:
                    self.draw_magic_triangle(nl, (nt, nb), fl, (ft, fb), is_side=True, color=wall_color)

            if right_wall == OPEN:
                pygame.draw.line(self.screen, wall_color, (nr, ft), (fr, ft), 2)
                pygame.draw.line(self.screen, wall_color, (nr, fb), (fr, fb), 2)
                pygame.draw.line(self.screen, wall_color, (fr, ft), (fr, fb), 2)
                pygame.draw.line(self.screen, wall_color, (nr, nt), (fr, ft), 2)
            else:
                pygame.draw.line(self.screen, wall_color, (nr, nt), (fr, ft), 2)
                pygame.draw.line(self.screen, wall_color, (nr, nb), (fr, fb), 2)
                pygame.draw.line(self.screen, wall_color, (fr, ft), (fr, fb), 2)
                if right_wall == DOOR:
                    self.draw_door_frame(nr, (nt, nb), fr, (ft, fb), is_side=True, color=wall_color)
                elif right_wall == MAGIC and magic_light:
                    self.draw_magic_triangle(nr, (nt, nb), fr, (ft, fb), is_side=True, color=wall_color)

            for m in monsters:
                if m.alive and (m.x, m.y) == (cx, cy):
                    if not m.is_magical or magic_light:
                        draw_box = (nl, nt, nr, nb) if depth == 0 else (fl, ft, fr, fb)
                        self.draw_monster_wireframe(m, draw_box, wall_color)

            if front_wall != OPEN:
                pygame.draw.line(self.screen, wall_color, (fl, ft), (fr, ft), 2)
                pygame.draw.line(self.screen, wall_color, (fl, fb), (fr, fb), 2)
                if front_wall == DOOR:
                    self.draw_door_frame(fl, ft, fr, fb, is_side=False, color=wall_color)
                elif front_wall == MAGIC and magic_light:
                    self.draw_magic_triangle(fl, ft, fr, fb, is_side=False, color=wall_color)
                break

            dx, dy = DIRS[pdir]
            cx += dx
            cy += dy

    def render_examine(self, room_items, backpack, active_torch, room_monsters, vert):
        self.screen.blit(self.font.render("IN THIS ROOM", True, GREEN), (315, 65))
        lines = [item.display_name for item in room_items]
        for m in room_monsters:
            lines.insert(0, f"!! {m.name} !!")
        if vert:
            if vert.get("down"):
                lines.append(f"[SHAFT DOWN: {vert['down']}]")
            if vert.get("up"):
                lines.append(f"[SHAFT UP: {vert['up']}]")

        if not lines:
            self.screen.blit(self.small_font.render("(NOTHING ON FLOOR)", True, DIM_GREEN), (90, 100))
        else:
            for idx, label in enumerate(lines):
                col = 90 if idx % 2 == 0 else 420
                row = 100 + (idx // 2) * 24
                c = RED if label.startswith("!!") else (CYAN if label.startswith("[") else GREEN)
                self.screen.blit(self.small_font.render(label, True, c), (col, row))

        pygame.draw.line(self.screen, GREEN, (75, 225), (725, 225), 2)
        self.screen.blit(self.font.render("BACKPACK", True, GREEN), (340, 240))

        if not backpack:
            self.screen.blit(self.small_font.render("(EMPTY)", True, DIM_GREEN), (90, 280))
        else:
            for idx, item in enumerate(backpack):
                col = 90 if idx % 2 == 0 else 420
                row = 280 + (idx // 2) * 24
                if item is active_torch and item.is_lit:
                    pygame.draw.rect(self.screen, GREEN, (col - 4, row - 2, 240, 20))
                    txt = self.small_font.render(item.display_name, True, BLACK)
                else:
                    txt = self.small_font.render(item.display_name, True, GREEN)
                self.screen.blit(txt, (col, row))

        hint = self.small_font.render("PRESS TAB OR TYPE 'LOOK' TO RETURN", True, DIM_GREEN)
        self.screen.blit(hint, (235, 415))

    def render_map(self, level, px, py, monsters, show_verticals=False):
        cell_px = 11
        ox = (self.width - 32 * cell_px) // 2
        oy = 65
        for y in range(32):
            for x in range(32):
                rect = (ox + x * cell_px, oy + y * cell_px, cell_px, cell_px)
                if level.is_open(x, y):
                    pygame.draw.rect(self.screen, DIM_GREEN, rect)
                else:
                    pygame.draw.rect(self.screen, GREEN, rect, 1)

        if show_verticals:
            for (vx, vy), info in level.verticals.items():
                vcx = ox + vx * cell_px + cell_px // 2
                vcy = oy + vy * cell_px + cell_px // 2
                col = CYAN if (info.get("down") == "LADDER" or info.get("up") == "LADDER") else AMBER
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
        vitals = state["vitals"]
        self.screen.fill(BLACK)
        pygame.draw.rect(self.screen, DIM_GREEN, (60, 45, 680, 400), 1)

        if state.get("victory"):
            msg = self.font.render("THE CROWN OF AETHER SHINES - VICTORY!", True, CYAN)
            sub = self.small_font.render("YOU HAVE CONQUERED THE DEPTHS OF CINDERS & ECHO!", True, GREEN)
            sub2 = self.small_font.render("TYPE 'RESTART' TO PLAY AGAIN", True, DIM_GREEN)
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 195))
            self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, 235))
            self.screen.blit(sub2, (self.width // 2 - sub2.get_width() // 2, 275))
        elif vitals.dead:
            msg = self.font.render("YOUR HEART HAS STOPPED - GAME OVER", True, RED)
            sub = self.small_font.render("TYPE 'RESTART' TO TRY AGAIN", True, GREEN)
            self.screen.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))
            self.screen.blit(sub, (self.width // 2 - sub.get_width() // 2, 255))
        elif vitals.fainted:
            msg = self.font.render("YOU HAVE FAINTED FROM EXHAUSTION...", True, AMBER)
            sub = self.small_font.render("RESTING UNTIL YOUR HEART RATE RECOVERS...", True, DIM_GREEN)
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
        right_surf = self.small_font.render(right_txt, True, GREEN)

        self.screen.blit(self.small_font.render(left_txt, True, GREEN), (60, 460))
        self.screen.blit(right_surf, (740 - right_surf.get_width(), 460))

        if vitals.dead:
            pygame.draw.line(self.screen, RED, (self.width // 2 - 18, 468), (self.width // 2 + 18, 468), 2)
        else:
            heart_color = GREEN
            if vitals.current_bpm >= vitals.faint_threshold - 20:
                heart_color = RED
            elif vitals.current_bpm >= 115:
                heart_color = AMBER
            heart_r = int(9 + 6 * state["pulse"])
            pygame.draw.circle(self.screen, heart_color, (self.width // 2, 468), heart_r, 2)

        self.screen.blit(self.small_font.render(state["status"], True, GREEN), (60, 505))
        prompt_text = "> [UNCONSCIOUS]" if (vitals.fainted and not vitals.dead) else f"> {state['cmd_buffer']}_"
        self.screen.blit(self.font.render(prompt_text, True, GREEN), (60, 535))
        pygame.display.flip()