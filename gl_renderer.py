import pygame
import moderngl
import numpy as np
import math
from maze import DIRS, DIR_NAMES, OPEN, DOOR, MAGIC, WALL

RAYCAST_VERT_SHADER = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    v_uv = in_pos * 0.5 + 0.5;
}
"""

RAYCAST_FRAG_SHADER = """
#version 330
in vec2 v_uv;

uniform sampler2D u_maze_tex;   // 32x32 RGBA8: R=North, G=East, B=South, A=West (0=OPEN, 1=WALL, 2=DOOR, 3=MAGIC)
uniform vec2 u_cam_pos;         // Continuous player position in tile units (px + 0.5, py + 0.5)
uniform float u_cam_angle;      // Continuous facing angle in radians (0=North, pi/2=East, pi=South, 3pi/2=West)
uniform float u_bob;            // Vertical head-bob offset
uniform float u_time;
uniform float u_flicker;
uniform float u_torch_range;
uniform int u_magic_light;
uniform vec3 u_light_color;

out vec4 f_color;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// Fetch wall boundary code (0=OPEN, 1=WALL, 2=DOOR, 3=MAGIC) for cell (cx, cy) and side (0=N,1=E,2=S,3=W)
int get_wall(ivec2 cell, int dir) {
    if (cell.x < 0 || cell.x >= 32 || cell.y < 0 || cell.y >= 32) return 1;
    vec4 texel = texelFetch(u_maze_tex, cell, 0);
    float v = (dir == 0) ? texel.r : ((dir == 1) ? texel.g : ((dir == 2) ? texel.b : texel.a));
    return int(round(v * 255.0));
}

vec3 eval_stone(vec2 uv, out vec3 normal) {
    vec2 grid = vec2(4.0, 6.0);
    vec2 st = uv * grid;
    float row = floor(st.y);
    st.x += mod(row, 2.0) * 0.5;
    vec2 cell = floor(st);
    vec2 f = fract(st);

    float mortar_x = smoothstep(0.0, 0.06, f.x) * smoothstep(1.0, 0.94, f.x);
    float mortar_y = smoothstep(0.0, 0.08, f.y) * smoothstep(1.0, 0.92, f.y);
    float brick_mask = mortar_x * mortar_y;

    float rnd = hash(cell);
    float grit = noise(uv * 36.0) * 0.25 + noise(uv * 108.0) * 0.14;
    vec3 base_stone = mix(vec3(0.06, 0.055, 0.05), vec3(0.34, 0.30, 0.26) + rnd * 0.12, brick_mask);
    base_stone += (grit - 0.18) * 0.20;

    float damp = smoothstep(0.62, 1.0, uv.y) * noise(uv * 12.0);
    base_stone = mix(base_stone, vec3(0.07, 0.15, 0.09), damp * 0.45);

    float nx = (smoothstep(0.0, 0.15, f.x) - smoothstep(0.85, 1.0, f.x)) + (noise(uv * 42.0) - 0.5) * 0.45;
    float ny = (smoothstep(0.0, 0.17, f.y) - smoothstep(0.83, 1.0, f.y)) + (noise(uv * 42.0 + 5.2) - 0.5) * 0.45;
    normal = normalize(vec3(nx, ny, 1.0));
    return base_stone;
}

vec3 eval_door(vec2 uv, out vec3 normal) {
    if (uv.x < 0.20 || uv.x > 0.80 || uv.y < 0.16) {
        return eval_stone(uv, normal);
    }
    vec2 duv = vec2((uv.x - 0.20) / 0.60, (uv.y - 0.16) / 0.84);
    float plank = floor(duv.x * 4.0);
    float seam = smoothstep(0.0, 0.05, fract(duv.x * 4.0)) * smoothstep(1.0, 0.95, fract(duv.x * 4.0));
    float grain = noise(vec2(duv.x * 48.0, duv.y * 8.0));
    vec3 wood = vec3(0.36, 0.20, 0.09) * (0.8 + 0.3 * hash(vec2(plank, 1.0)) + 0.2 * grain);
    wood *= (0.42 + 0.58 * seam);

    float band1 = smoothstep(0.045, 0.02, abs(duv.y - 0.24));
    float band2 = smoothstep(0.045, 0.02, abs(duv.y - 0.78));
    float iron = max(band1, band2);
    vec3 col = mix(wood, vec3(0.18, 0.19, 0.22), iron);

    float ring = smoothstep(0.025, 0.01, abs(length(duv - vec2(0.72, 0.52)) - 0.07));
    col = mix(col, vec3(0.45, 0.47, 0.52), ring);

    normal = normalize(vec3((seam - 0.5) * 0.5, iron * 0.4, 1.0));
    return col;
}

void main() {
    vec2 dir = vec2(sin(u_cam_angle), -cos(u_cam_angle));
    vec2 plane = vec2(cos(u_cam_angle), sin(u_cam_angle)) * 0.82;

    float cam_x = (v_uv.x * 2.0 - 1.0);
    vec2 ray_dir = dir + plane * cam_x;

    ivec2 map_cell = ivec2(floor(u_cam_pos));
    vec2 delta_dist = abs(vec2(1.0) / (ray_dir + vec2(1e-6)));

    ivec2 step_dir;
    vec2 side_dist;
    if (ray_dir.x < 0.0) {
        step_dir.x = -1;
        side_dist.x = (u_cam_pos.x - float(map_cell.x)) * delta_dist.x;
    } else {
        step_dir.x = 1;
        side_dist.x = (float(map_cell.x) + 1.0 - u_cam_pos.x) * delta_dist.x;
    }
    if (ray_dir.y < 0.0) {
        step_dir.y = -1;
        side_dist.y = (u_cam_pos.y - float(map_cell.y)) * delta_dist.y;
    } else {
        step_dir.y = 1;
        side_dist.y = (float(map_cell.y) + 1.0 - u_cam_pos.y) * delta_dist.y;
    }

    float perp_dist = u_torch_range + 1.0;
    int hit_wall_type = 0;
    int hit_side = 0;
    float wall_u = 0.0;

    for (int i = 0; i < 16; i++) {
        if (side_dist.x < side_dist.y) {
            int exit_dir = (step_dir.x > 0) ? 1 : 3;
            int w = get_wall(map_cell, exit_dir);
            if (w != 0) {
                perp_dist = side_dist.x;
                hit_wall_type = w;
                hit_side = 0;
                wall_u = fract(u_cam_pos.y + perp_dist * ray_dir.y);
                if (step_dir.x < 0) wall_u = 1.0 - wall_u;
                break;
            }
            side_dist.x += delta_dist.x;
            map_cell.x += step_dir.x;
        } else {
            int exit_dir = (step_dir.y > 0) ? 2 : 0;
            int w = get_wall(map_cell, exit_dir);
            if (w != 0) {
                perp_dist = side_dist.y;
                hit_wall_type = w;
                hit_side = 1;
                wall_u = fract(u_cam_pos.x + perp_dist * ray_dir.x);
                if (step_dir.y > 0) wall_u = 1.0 - wall_u;
                break;
            }
            side_dist.y += delta_dist.y;
            map_cell.y += step_dir.y;
        }
        if (min(side_dist.x, side_dist.y) > u_torch_range + 1.0) break;
    }

    float horizon = 0.5 + u_bob;
    float line_h = 0.88 / max(0.08, perp_dist);
    float wall_top = horizon + line_h * 0.5;
    float wall_bot = horizon - line_h * 0.5;

    vec3 fog_color = vec3(0.02, 0.018, 0.016);
    vec3 final_col = fog_color;

    if (v_uv.y <= wall_top && v_uv.y >= wall_bot && hit_wall_type != 0) {
        float wall_v = (wall_top - v_uv.y) / max(0.0001, (wall_top - wall_bot));
        vec2 uv = vec2(wall_u, wall_v);
        vec3 normal = vec3(0.0, 0.0, 1.0);
        vec3 albedo = vec3(0.1);
        float rune_glow = 0.0;

        // 1=WALL (Stone), 2=DOOR (Iron-banded Oak Door), 3=MAGIC (Arcane Rune Wall)
        if (hit_wall_type == 2) {
            albedo = eval_door(uv, normal);
        } else if (hit_wall_type == 3 && u_magic_light == 1) {
            albedo = eval_stone(uv, normal);
            vec2 p = (uv - vec2(0.5, 0.62)) * vec2(1.4, 1.2);
            float tri = max(abs(p.x) * 1.73205 + p.y, -p.y * 2.0) - 0.45;
            float edge = smoothstep(0.045, 0.0, abs(tri));
            float inner = smoothstep(0.03, 0.0, abs(length(p - vec2(0.0, 0.05)) - 0.14));
            rune_glow = max(edge, inner) * (0.8 + 0.2 * sin(u_time * 4.0));
        } else {
            albedo = eval_stone(uv, normal);
        }

        float corner_ao = smoothstep(0.0, 0.06, wall_u) * smoothstep(1.0, 0.94, wall_u);
        albedo *= (0.65 + 0.35 * corner_ao);

        float axis_shade = (hit_side == 1) ? 1.0 : 0.78;

        if (u_magic_light == 1) {
            albedo = mix(albedo, albedo * vec3(0.85, 0.96, 1.18), 0.35);
        }

        float norm_d = clamp(perp_dist / max(1.0, u_torch_range), 0.0, 1.0);
        float atten = pow(1.0 - norm_d, 1.35) * u_flicker * 1.45;
        vec3 light_dir = normalize(vec3((0.5 - v_uv.x) * 0.6, (0.5 - v_uv.y) * 0.6, 0.9));
        float diff = max(0.35, dot(normal, light_dir)) * axis_shade;

        vec3 lit = albedo * u_light_color * diff * atten;
        lit += vec3(0.22, 0.85, 1.0) * rune_glow * 1.5;
        final_col = mix(fog_color, lit, clamp(atten * 1.15, 0.0, 1.0));
        final_col += vec3(0.20, 0.85, 1.0) * rune_glow * 0.9;
    } else {
        bool is_ceil = (v_uv.y > horizon);
        float dy = abs(v_uv.y - horizon);
        float row_dist = 0.44 / max(0.002, dy);
        vec2 world_pos = u_cam_pos + ray_dir * row_dist;
        vec2 tile_uv = fract(world_pos);

        vec3 normal;
        vec3 albedo = eval_stone(tile_uv * 2.0, normal) * (is_ceil ? 0.65 : 0.85);
        if (u_magic_light == 1) {
            albedo = mix(albedo, albedo * vec3(0.85, 0.96, 1.18), 0.35);
        }
        float norm_d = clamp(row_dist / max(1.0, u_torch_range), 0.0, 1.0);
        float atten = pow(1.0 - norm_d, 1.45) * u_flicker * 1.3;
        vec3 lit = albedo * u_light_color * atten;
        final_col = mix(fog_color, lit, clamp(atten * 1.15, 0.0, 1.0));
    }

    f_color = vec4(final_col, 1.0);
}
"""

OVERLAY_VERT_SHADER = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    v_uv = in_uv;
}
"""

OVERLAY_FRAG_SHADER = """
#version 330
in vec2 v_uv;
uniform sampler2D u_tex;
out vec4 f_color;
void main() {
    f_color = texture(u_tex, v_uv);
}
"""


class ModernGLRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.ray_prog = self.ctx.program(
            vertex_shader=RAYCAST_VERT_SHADER,
            fragment_shader=RAYCAST_FRAG_SHADER,
        )
        self.overlay_prog = self.ctx.program(
            vertex_shader=OVERLAY_VERT_SHADER,
            fragment_shader=OVERLAY_FRAG_SHADER,
        )

        quad_data = np.array([
            -1.0,  1.0, 0.0, 0.0,
            -1.0, -1.0, 0.0, 1.0,
             1.0,  1.0, 1.0, 0.0,
             1.0, -1.0, 1.0, 1.0,
        ], dtype="f4")
        self.quad_vbo = self.ctx.buffer(quad_data.tobytes())
        self.quad_vao = self.ctx.simple_vertex_array(self.overlay_prog, self.quad_vbo, "in_pos", "in_uv")

        vp_quad = np.array([
            -1.0,  1.0,
            -1.0, -1.0,
             1.0,  1.0,
             1.0, -1.0,
        ], dtype="f4")
        self.vp_vbo = self.ctx.buffer(vp_quad.tobytes())
        self.vp_vao = self.ctx.simple_vertex_array(self.ray_prog, self.vp_vbo, "in_pos")

        self.maze_tex = self.ctx.texture((32, 32), 4)
        self.maze_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._cached_level_id = None

        self.hud_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.hud_tex = self.ctx.texture((self.width, self.height), 4)
        self.hud_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

        self.font = pygame.font.SysFont("consolas", 20, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 15, bold=True)
        self.time_accum = 0.0

        self.cam_x = None
        self.cam_y = None
        self.cam_angle = None
        self.bob_phase = 0.0
        self.visited_tiles = {}

    def _sync_maze_texture(self, level):
        if id(level) == self._cached_level_id:
            return
        self._cached_level_id = id(level)
        arr = np.zeros((32, 32, 4), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                cell = level.grid[y][x]
                arr[y, x] = [cell[0], cell[1], cell[2], cell[3]]
        self.maze_tex.write(arr.tobytes())

    def blit_pygame_surface(self, surf):
        raw = pygame.image.tostring(surf, "RGBA", False)
        self.hud_tex.write(raw)
        self.hud_tex.use(0)
        self.overlay_prog["u_tex"].value = 0
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)

    def _draw_soft_glow(self, surf, center, max_r, rgb, peak_alpha):
        glow_surf = pygame.Surface((max_r * 2, max_r * 2), pygame.SRCALPHA)
        for step in range(8, 0, -1):
            frac = step / 8.0
            r = max(2, int(max_r * frac))
            a = int(peak_alpha * ((1.0 - frac) ** 1.6 + 0.15))
            pygame.draw.circle(glow_surf, (rgb[0], rgb[1], rgb[2], min(255, a)), (max_r, max_r), r)
        surf.blit(glow_surf, (int(center[0] - max_r), int(center[1] - max_r)))

    def _draw_first_person_hands(self, surf, left_item, right_item, active_torch, flicker, bob_px):
        if active_torch and active_torch.is_lit and not right_item:
            col = (100, 205, 255) if active_torch.magic_light else (255, 165, 55)
            self._draw_soft_glow(surf, (710, int(395 + bob_px)), int(78 * flicker), col, 48)

        if left_item:
            lx, ly = 155, int(418 + bob_px * 1.4)
            if left_item.item_class == "WEAPON":
                blade_col = (130, 215, 255) if left_item.is_magical else (195, 202, 214)
                edge_col = (235, 242, 255) if left_item.is_magical else (145, 152, 165)
                blade_pts = [
                    (lx + 12, ly - 24),
                    (lx + 138, ly - 248),
                    (lx + 156, ly - 266),
                    (lx + 152, ly - 236),
                    (lx + 34, ly - 16),
                ]
                pygame.draw.polygon(surf, blade_col, blade_pts)
                pygame.draw.polygon(surf, (45, 48, 55), blade_pts, 2)
                pygame.draw.line(surf, edge_col, (lx + 23, ly - 20), (lx + 148, ly - 252), 3)
                pygame.draw.polygon(surf, (130, 98, 56), [(lx - 14, ly - 32), (lx + 54, ly - 14), (lx + 50, ly - 4), (lx - 18, ly - 22)])
                pygame.draw.polygon(surf, (60, 44, 24), [(lx - 14, ly - 32), (lx + 54, ly - 14), (lx + 50, ly - 4), (lx - 18, ly - 22)], 2)
            elif left_item.item_class == "SHIELD":
                pygame.draw.ellipse(surf, (95, 68, 42), (lx - 45, ly - 155, 115, 145))
                pygame.draw.ellipse(surf, (155, 160, 170), (lx - 45, ly - 155, 115, 145), 5)
            else:
                pygame.draw.circle(surf, (195, 165, 95), (lx + 15, ly - 45), 22)

            pygame.draw.polygon(surf, (68, 48, 32), [(lx - 70, 443), (lx - 12, ly - 22), (lx + 36, ly - 10), (lx + 8, 443)])
            pygame.draw.ellipse(surf, (86, 62, 42), (lx - 10, ly - 32, 44, 34))
            pygame.draw.ellipse(surf, (42, 30, 20), (lx - 10, ly - 32, 44, 34), 2)

        if right_item:
            rx, ry = 645, int(418 + bob_px * 1.4)
            if right_item.item_class == "TORCH":
                pygame.draw.polygon(surf, (88, 56, 30), [(rx - 15, ry + 10), (rx - 45, ry - 145), (rx - 22, ry - 148), (rx + 8, ry + 8)])
                if right_item.is_lit or right_item.minutes_left > 0:
                    col = (110, 210, 255) if right_item.magic_light else (255, 165, 50)
                    self._draw_soft_glow(surf, (rx - 35, ry - 165), int(65 * flicker), col, 85)
                    flame_core = (220, 245, 255) if right_item.magic_light else (255, 225, 110)
                    pygame.draw.ellipse(surf, (255, 120, 25), (rx - 48, ry - 190, 28, 45))
                    pygame.draw.ellipse(surf, flame_core, (rx - 42, ry - 180, 16, 30))
            elif right_item.item_class == "WEAPON":
                blade_col = (130, 215, 255) if right_item.is_magical else (195, 202, 214)
                blade_pts = [
                    (rx - 12, ry - 24),
                    (rx - 138, ry - 248),
                    (rx - 156, ry - 266),
                    (rx - 152, ry - 236),
                    (rx - 34, ry - 16),
                ]
                pygame.draw.polygon(surf, blade_col, blade_pts)
                pygame.draw.polygon(surf, (45, 48, 55), blade_pts, 2)
                pygame.draw.polygon(surf, (130, 98, 56), [(rx + 14, ry - 32), (rx - 54, ry - 14), (rx - 50, ry - 4), (rx + 18, ry - 22)])
            else:
                pygame.draw.circle(surf, (195, 165, 95), (rx - 15, ry - 45), 22)

            pygame.draw.polygon(surf, (68, 48, 32), [(rx + 70, 443), (rx + 12, ry - 22), (rx - 36, ry - 10), (rx - 8, 443)])
            pygame.draw.ellipse(surf, (86, 62, 42), (rx - 34, ry - 32, 44, 34))
            pygame.draw.ellipse(surf, (42, 30, 20), (rx - 34, ry - 32, 44, 34), 2)

    def _draw_corner_radar(self, surf, level, lvl_idx, px, py, cam_angle):
        visited = self.visited_tiles.setdefault(lvl_idx, set())
        visited.add((px, py))

        radius = 3
        cell_sz = 14
        radar_w = (radius * 2 + 1) * cell_sz + 8
        rx0 = 740 - radar_w - 8
        ry0 = 53

        panel = pygame.Surface((radar_w, radar_w), pygame.SRCALPHA)
        panel.fill((14, 12, 10, 205))
        pygame.draw.rect(panel, (115, 92, 62, 235), (0, 0, radar_w, radar_w), 2)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                gx, gy = px + dx, py + dy
                bx = 4 + (dx + radius) * cell_sz
                by = 4 + (dy + radius) * cell_sz
                if 0 <= gx < 32 and 0 <= gy < 32 and level.is_open(gx, gy):
                    is_vis = (gx, gy) in visited
                    fill = (78, 66, 48, 220) if is_vis else (42, 36, 28, 170)
                    pygame.draw.rect(panel, fill, (bx + 1, by + 1, cell_sz - 2, cell_sz - 2))
                    cell = level.grid[gy][gx]
                    if cell[0] == DOOR:
                        pygame.draw.line(panel, (210, 145, 65), (bx + 2, by), (bx + cell_sz - 2, by), 2)
                    if cell[1] == DOOR:
                        pygame.draw.line(panel, (210, 145, 65), (bx + cell_sz, by + 2), (bx + cell_sz, by + cell_sz - 2), 2)

        cx = 4 + radius * cell_sz + cell_sz // 2
        cy = 4 + radius * cell_sz + cell_sz // 2
        pygame.draw.circle(panel, (255, 200, 60), (cx, cy), 4)
        ax = cx + math.sin(cam_angle) * 8
        ay = cy - math.cos(cam_angle) * 8
        pygame.draw.line(panel, (255, 255, 255), (cx, cy), (ax, ay), 2)

        surf.blit(panel, (rx0, ry0))

    def _draw_bronze_hud(self, surf, state, vitals):
        pygame.draw.rect(surf, (48, 40, 32), (56, 41, 688, 408), 4)
        pygame.draw.rect(surf, (115, 92, 62), (58, 43, 684, 404), 2)

        level = state["level"]
        px, py, pdir = state["px"], state["py"], state["pdir"]
        cell = level.grid[py][px]
        exits = []
        if cell[(pdir - 1) % 4] in (OPEN, DOOR, MAGIC):
            exits.append("L")
        if cell[pdir] in (OPEN, DOOR, MAGIC):
            exits.append("FWD")
        if cell[(pdir + 1) % 4] in (OPEN, DOOR, MAGIC):
            exits.append("R")
        exit_str = "/".join(exits) if exits else "DEAD END"
        comp_txt = f"FL {state['level_idx'] + 1} • {DIR_NAMES[pdir]} ({exit_str})"
        comp_surf = self.small_font.render(comp_txt, True, (225, 195, 130))
        pill_w = comp_surf.get_width() + 24
        pill_rect = pygame.Rect(self.width // 2 - pill_w // 2, 28, pill_w, 24)
        pygame.draw.rect(surf, (24, 20, 17), pill_rect, border_radius=5)
        pygame.draw.rect(surf, (115, 92, 62), pill_rect, 2, border_radius=5)
        surf.blit(comp_surf, (self.width // 2 - comp_surf.get_width() // 2, 32))

        bar_rect = pygame.Rect(275, 434, 250, 58)
        pygame.draw.rect(surf, (26, 22, 19), bar_rect, border_radius=6)
        pygame.draw.rect(surf, (125, 98, 64), bar_rect, 3, border_radius=6)

        l_box = pygame.Rect(288, 443, 56, 40)
        r_box = pygame.Rect(456, 443, 56, 40)
        for box in (l_box, r_box):
            pygame.draw.rect(surf, (16, 14, 12), box)
            pygame.draw.rect(surf, (95, 75, 50), box, 2)

        left_txt = state["left_hand"].display_name if state["left_hand"] else "EMPTY"
        right_txt = state["right_hand"].display_name if state["right_hand"] else "EMPTY"
        l_label = self.small_font.render(left_txt, True, (215, 185, 125))
        r_label = self.small_font.render(right_txt, True, (215, 185, 125))
        surf.blit(l_label, (265 - l_label.get_width(), 456))
        surf.blit(r_label, (535, 456))

        cx, cy = self.width // 2, 463
        pygame.draw.circle(surf, (20, 14, 14), (cx, cy), 28)
        pygame.draw.circle(surf, (140, 108, 68), (cx, cy), 28, 3)

        if vitals.dead:
            pygame.draw.line(surf, (220, 40, 40), (cx - 14, cy), (cx + 14, cy), 3)
        else:
            pulse = state["pulse"]
            r = int(11 + 6 * pulse)
            glow = (255, 45, 55) if vitals.current_bpm >= 115 else (215, 30, 45)
            pygame.draw.circle(surf, glow, (cx - r // 2, cy - r // 4), int(r * 0.65))
            pygame.draw.circle(surf, glow, (cx + r // 2, cy - r // 4), int(r * 0.65))
            pygame.draw.polygon(surf, glow, [(cx - int(r * 1.1), cy - r // 6), (cx + int(r * 1.1), cy - r // 6), (cx, cy + int(r * 1.15))])

        status_surf = self.small_font.render(state["status"], True, (225, 195, 130))
        surf.blit(status_surf, (60, 505))
        prompt_text = "> [UNCONSCIOUS]" if (vitals.fainted and not vitals.dead) else f"> {state['cmd_buffer']}_"
        surf.blit(self.font.render(prompt_text, True, (235, 205, 140)), (60, 535))

    def _draw_billboard_entities(self, surf, state, cam_x, cam_y, cam_angle, torch_range, magic_light, flicker):
        fwd_x, fwd_y = math.sin(cam_angle), -math.cos(cam_angle)
        right_x, right_y = math.cos(cam_angle), math.sin(cam_angle)

        for (fx, fy), items in state["floor_items"].items():
            if not items:
                continue
            dx = (fx + 0.5) - cam_x
            dy = (fy + 0.5) - cam_y
            depth = dx * fwd_x + dy * fwd_y
            side = dx * right_x + dy * right_y
            if 0.25 < depth < torch_range and abs(side) < depth * 0.95:
                sx = 400 + (side / (depth * 0.82)) * 340
                sy = 245 + (0.44 / depth) * 400 - 6
                iw = max(6, int(65 / depth))
                ih = max(3, int(14 / depth))
                atten = max(0.25, (1.0 - depth / torch_range) ** 1.2) * flicker
                pygame.draw.rect(surf, (int(240 * atten), int(195 * atten), int(95 * atten)), (int(sx - iw / 2), int(sy - ih), iw, ih))

        visible_mons = []
        for m in state["monsters"]:
            if not m.alive or (m.is_magical and not magic_light):
                continue
            dx = (m.x + 0.5) - cam_x
            dy = (m.y + 0.5) - cam_y
            depth = dx * fwd_x + dy * fwd_y
            side = dx * right_x + dy * right_y
            if 0.20 < depth < torch_range and abs(side) < depth * 0.95:
                visible_mons.append((depth, side, m))

        visible_mons.sort(key=lambda item: item[0], reverse=True)
        for depth, side, m in visible_mons:
            sx = 400 + (side / (depth * 0.82)) * 340
            h = (0.88 / depth) * 400
            w = h * 0.85
            y_bot = 245 + h * 0.5
            y_top = y_bot - h
            atten = max(0.25, (1.0 - depth / torch_range) ** 1.2) * flicker
            self._draw_shaded_monster(surf, m, (sx - w / 2, y_top, sx + w / 2, y_bot), atten)

    def _draw_shaded_monster(self, surf, monster, rect, brightness):
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) / 2
        w = x2 - x1
        h = y2 - y1
        bottom = y2 - h * 0.04
        b = max(0.22, min(1.0, brightness))

        def shade(rgb):
            return (int(rgb[0] * b), int(rgb[1] * b), int(rgb[2] * b))

        pygame.draw.ellipse(surf, (10, 8, 8, 180), (cx - w * 0.24, bottom - h * 0.04, w * 0.48, h * 0.07))

        if monster.shape == "SPIDER":
            body_y = bottom - h * 0.14
            r = max(5, int(w * 0.095))
            for side in (-1, 1):
                for leg in range(3):
                    spread = (0.16 + leg * 0.075) * w * side
                    knee_y = body_y - h * (0.10 - leg * 0.02)
                    pygame.draw.line(surf, shade((55, 46, 52)), (cx, body_y), (cx + spread * 0.6, knee_y), max(2, int(w * 0.016)))
                    pygame.draw.line(surf, shade((38, 32, 36)), (cx + spread * 0.6, knee_y), (cx + spread, bottom), max(2, int(w * 0.013)))
            pygame.draw.circle(surf, shade((65, 32, 42)), (int(cx), int(body_y)), r)
            pygame.draw.circle(surf, (255, 45, 45), (int(cx - r * 0.35), int(body_y - r * 0.2)), max(1, int(r * 0.2)))
            pygame.draw.circle(surf, (255, 45, 45), (int(cx + r * 0.35), int(body_y - r * 0.2)), max(1, int(r * 0.2)))
        elif monster.shape == "SNAKE":
            pts = [
                (cx - w * 0.14, bottom),
                (cx + w * 0.12, bottom - h * 0.12),
                (cx - w * 0.10, bottom - h * 0.26),
                (cx + w * 0.06, bottom - h * 0.40),
                (cx - w * 0.03, bottom - h * 0.44),
            ]
            pygame.draw.lines(surf, shade((50, 165, 72)), False, pts, max(3, int(w * 0.035)))
        elif monster.shape == "BLOB":
            top_y = bottom - h * 0.44
            pygame.draw.ellipse(surf, shade((45, 195, 120)), (cx - w * 0.23, top_y, w * 0.46, h * 0.44))
        elif monster.shape in ("GIANT", "KNIGHT"):
            top_y = bottom - h * 0.72
            bw = w * 0.28
            armor_col = (145, 152, 165) if monster.shape == "KNIGHT" else (140, 120, 102)
            pygame.draw.rect(surf, shade(armor_col), (cx - bw / 2, top_y + h * 0.14, bw, h * 0.36))
            pygame.draw.circle(surf, shade(armor_col), (int(cx), int(top_y + h * 0.07)), max(3, int(w * 0.075)))
        else:
            top_y = bottom - h * 0.76
            cloak_col = (105, 175, 255) if monster.shape == "WRAITH" else (195, 85, 245)
            pygame.draw.polygon(surf, shade(cloak_col), [(cx, top_y), (cx - w * 0.23, bottom), (cx + w * 0.23, bottom)])

    def _draw_examine_overlay(self, surf, room_items, backpack, active_torch, room_monsters, vert):
        gold = (230, 195, 110)
        dim = (150, 140, 115)
        red = (255, 65, 65)
        cyan = (90, 220, 255)

        surf.blit(self.font.render("IN THIS ROOM", True, gold), (325, 65))
        lines = [item.display_name for item in room_items]
        for m in room_monsters:
            lines.insert(0, f"!! {m.name} !!")
        if vert:
            if vert.get("down"):
                lines.append(f"[SHAFT DOWN: {vert['down']}]")
            if vert.get("up"):
                lines.append(f"[SHAFT UP: {vert['up']}]")

        if not lines:
            surf.blit(self.small_font.render("(NOTHING ON FLOOR)", True, dim), (90, 102))
        else:
            for idx, label in enumerate(lines):
                col = 90 if idx % 2 == 0 else 420
                row = 102 + (idx // 2) * 24
                c = red if label.startswith("!!") else (cyan if label.startswith("[") else gold)
                surf.blit(self.small_font.render(label, True, c), (col, row))

        pygame.draw.line(surf, (125, 98, 64), (75, 225), (725, 225), 2)
        surf.blit(self.font.render("BACKPACK", True, gold), (345, 240))

        if not backpack:
            surf.blit(self.small_font.render("(EMPTY)", True, dim), (90, 280))
        else:
            for idx, item in enumerate(backpack):
                col = 90 if idx % 2 == 0 else 420
                row = 280 + (idx // 2) * 24
                if item is active_torch and item.is_lit:
                    pygame.draw.rect(surf, (230, 165, 55), (col - 4, row - 2, 250, 20), border_radius=3)
                    txt = self.small_font.render(item.display_name, True, (18, 15, 12))
                else:
                    txt = self.small_font.render(item.display_name, True, gold)
                surf.blit(txt, (col, row))

        hint = self.small_font.render("PRESS TAB OR TYPE 'LOOK' TO RETURN", True, dim)
        surf.blit(hint, (245, 412))

    def _draw_map_overlay(self, surf, level, px, py, pdir, monsters, show_verticals=False):
        cell_px = 11
        ox = (self.width - 32 * cell_px) // 2
        oy = 62
        for y in range(32):
            for x in range(32):
                rect = (ox + x * cell_px, oy + y * cell_px, cell_px, cell_px)
                if level.is_open(x, y):
                    pygame.draw.rect(surf, (88, 74, 52), rect)
                else:
                    pygame.draw.rect(surf, (32, 28, 22), rect, 1)

        if show_verticals:
            for (vx, vy), info in level.verticals.items():
                vcx = ox + vx * cell_px + cell_px // 2
                vcy = oy + vy * cell_px + cell_px // 2
                col = (90, 220, 255) if (info.get("down") == "LADDER" or info.get("up") == "LADDER") else (230, 195, 110)
                pygame.draw.rect(surf, col, (vcx - 3, vcy - 3, 6, 6))

        for m in monsters:
            if m.alive:
                mcx = ox + m.x * cell_px + cell_px // 2
                mcy = oy + m.y * cell_px + cell_px // 2
                pygame.draw.circle(surf, (255, 55, 55), (mcx, mcy), 3)

        pcx = ox + px * cell_px + cell_px // 2
        pcy = oy + py * cell_px + cell_px // 2
        pygame.draw.circle(surf, (255, 200, 60), (pcx, pcy), 4)
        dx, dy = DIRS[pdir]
        pygame.draw.line(surf, (255, 255, 255), (pcx, pcy), (pcx + dx * 7, pcy + dy * 7), 2)

    def render_frame(self, state):
        dt = 0.016
        self.time_accum += dt
        vitals = state["vitals"]
        self.ctx.clear(0.03, 0.028, 0.025, 1.0)
        self.hud_surface.fill((0, 0, 0, 0))

        target_x = state["px"] + 0.5
        target_y = state["py"] + 0.5
        target_angle = state["pdir"] * (math.pi / 2.0)

        if self.cam_x is None or abs(target_x - self.cam_x) > 3.0 or abs(target_y - self.cam_y) > 3.0:
            self.cam_x, self.cam_y, self.cam_angle = target_x, target_y, target_angle
        else:
            move_dist = math.hypot(target_x - self.cam_x, target_y - self.cam_y)
            self.cam_x += (target_x - self.cam_x) * min(1.0, dt * 12.0)
            self.cam_y += (target_y - self.cam_y) * min(1.0, dt * 12.0)
            if move_dist > 0.03:
                self.bob_phase += dt * 16.0

            ang_diff = (target_angle - self.cam_angle + math.pi) % (2.0 * math.pi) - math.pi
            self.cam_angle = (self.cam_angle + ang_diff * min(1.0, dt * 14.0)) % (2.0 * math.pi)

        bob_val = math.sin(self.bob_phase) * 0.014 if math.hypot(target_x - self.cam_x, target_y - self.cam_y) > 0.03 else 0.0
        bob_px = bob_val * 400.0

        active_torch = state["active_torch"]
        lit = active_torch is not None and active_torch.is_lit and active_torch.torch_range > 0

        if not vitals.dead and not vitals.fainted and not state.get("victory"):
            mode = state["view_mode"]
            if mode == "EXAMINE":
                room_items = state["floor_items"].get((state["px"], state["py"]), [])
                room_monsters = [m for m in state["monsters"] if m.alive and (m.x, m.y) == (state["px"], state["py"])]
                vert = state["level"].verticals.get((state["px"], state["py"]))
                self._draw_examine_overlay(self.hud_surface, room_items, state["backpack"], active_torch, room_monsters, vert)
            elif mode in ("MAP", "VISION_MAP"):
                self._draw_map_overlay(self.hud_surface, state["level"], state["px"], state["py"], state["pdir"], state["monsters"], show_verticals=(mode == "VISION_MAP"))
            elif not lit:
                msg = self.small_font.render("IT IS PITCH DARK. (PULL A TORCH AND USE IT)", True, (90, 145, 95))
                self.hud_surface.blit(msg, (self.width // 2 - msg.get_width() // 2, 235))
            else:
                flicker = 0.92 + 0.08 * math.sin(self.time_accum * 10.5) * math.cos(self.time_accum * 6.7)
                if active_torch.minutes_left <= 5:
                    flicker *= 0.55

                light_col = (0.78, 0.92, 1.0) if active_torch.magic_light else (1.0, 0.74, 0.42)
                torch_range = float(active_torch.torch_range)
                magic_light = active_torch.magic_light

                self._sync_maze_texture(state["level"])
                self.maze_tex.use(0)
                self.ray_prog["u_maze_tex"].value = 0
                self.ray_prog["u_cam_pos"].value = (self.cam_x, self.cam_y)
                self.ray_prog["u_cam_angle"].value = self.cam_angle
                self.ray_prog["u_bob"].value = bob_val
                self.ray_prog["u_time"].value = self.time_accum
                self.ray_prog["u_flicker"].value = flicker
                self.ray_prog["u_torch_range"].value = torch_range
                self.ray_prog["u_magic_light"].value = 1 if magic_light else 0
                self.ray_prog["u_light_color"].value = light_col

                self.ctx.viewport = (60, 155, 680, 400)
                self.vp_vao.render(moderngl.TRIANGLE_STRIP)
                self.ctx.viewport = (0, 0, self.width, self.height)

                self.hud_surface.set_clip(pygame.Rect(60, 45, 680, 400))
                self._draw_billboard_entities(self.hud_surface, state, self.cam_x, self.cam_y, self.cam_angle, torch_range, magic_light, flicker)
                self._draw_first_person_hands(self.hud_surface, state["left_hand"], state["right_hand"], active_torch, flicker, bob_px)
                self.hud_surface.set_clip(None)

                self._draw_corner_radar(self.hud_surface, state["level"], state["level_idx"], state["px"], state["py"], self.cam_angle)

        elif state.get("victory"):
            msg = self.font.render("THE CROWN OF AETHER SHINES - VICTORY!", True, (90, 220, 255))
            self.hud_surface.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))
        elif vitals.dead:
            msg = self.font.render("YOUR HEART HAS STOPPED - GAME OVER", True, (255, 60, 60))
            self.hud_surface.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))
        elif vitals.fainted:
            msg = self.font.render("YOU HAVE FAINTED FROM EXHAUSTION...", True, (255, 180, 50))
            self.hud_surface.blit(msg, (self.width // 2 - msg.get_width() // 2, 215))

        self._draw_bronze_hud(self.hud_surface, state, vitals)
        self.blit_pygame_surface(self.hud_surface)
        pygame.display.flip()