import pygame
import sys
import math
import random
import json
import os
from maze import DungeonLevel, DIRS, DIR_NAMES, OPEN, DOOR, MAGIC
from inventory import GameItem, spawn_level_loot
from vitals import VitalsSystem
from monsters import Monster, spawn_level_monsters
from renderer import WireframeRenderer
from hd_renderer import HDRenderer
from gl_renderer import ModernGLRenderer
from audio import SoundEngine
from controls import InputController

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("Cinders & Echo")

offscreen_2d = pygame.Surface((800, 600))
wire_renderer = WireframeRenderer(offscreen_2d)
hd_renderer = HDRenderer(offscreen_2d)
gl_renderer = ModernGLRenderer(screen)
sound = SoundEngine()
controls = InputController()
gfx_mode = "MODERN"  # "MODERN", "HD", or "WIREFRAME"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "saves")
os.makedirs(SAVE_DIR, exist_ok=True)


def _get_save_path(slot_name=""):
    clean = "".join(c for c in slot_name.upper() if c.isalnum()) or "SAVEGAME"
    return os.path.join(SAVE_DIR, f"{clean}.json")


def _build_floor_data(lvl_idx):
    lvl = DungeonLevel(level_num=lvl_idx)
    return {
        "level": lvl,
        "floor_items": spawn_level_loot(lvl),
        "monsters": spawn_level_monsters(lvl),
    }


def create_new_game():
    floors = {0: _build_floor_data(0)}
    f0 = floors[0]
    starting_pack = [
        GameItem("PINE", "TORCH", revealed=True, reveal_req=5, torch_range=6, magic_light=False, minutes_left=15, damage=4),
        GameItem("WOODEN", "SWORD", revealed=True, reveal_req=5, swing_exertion=6.0, damage=12),
    ]
    pad_note = f" | PAD: {controls.controller_name[:16]}" if controls.controller_name else ""
    return {
        "floors": floors,
        "level_idx": 0,
        "level": f0["level"],
        "px": f0["level"].spawn_pos[0],
        "py": f0["level"].spawn_pos[1],
        "pdir": 0,
        "left_hand": None,
        "right_hand": None,
        "backpack": starting_pack,
        "active_torch": None,
        "floor_items": f0["floor_items"],
        "monsters": f0["monsters"],
        "vitals": VitalsSystem(starting_strength=100),
        "weight": sum(i.weight for i in starting_pack),
        "view_mode": "3D",
        "cmd_buffer": "",
        "status": f"CINDERS & ECHO | ENTER: TYPE CMD | TAB: BAG | WASD: MOVE{pad_note}",
        "pulse": 0.0,
        "time_scale": 1.0,
        "victory": False,
    }


state = create_new_game()


def switch_floor(new_idx, keep_pos=False):
    cur = state["level_idx"]
    state["floors"][cur] = {
        "level": state["level"],
        "floor_items": state["floor_items"],
        "monsters": state["monsters"],
    }
    if new_idx not in state["floors"]:
        state["floors"][new_idx] = _build_floor_data(new_idx)

    nxt = state["floors"][new_idx]
    state["level_idx"] = new_idx
    state["level"] = nxt["level"]
    state["floor_items"] = nxt["floor_items"]
    state["monsters"] = nxt["monsters"]
    if not keep_pos:
        state["px"], state["py"] = nxt["level"].spawn_pos


def recalc_weight():
    total = sum(i.weight for i in state["backpack"])
    if state["left_hand"]:
        total += state["left_hand"].weight
    if state["right_hand"]:
        total += state["right_hand"].weight
    state["weight"] = total


def parse_hand(arg):
    if arg in ("L", "LEFT"):
        return "left_hand"
    if arg in ("R", "RIGHT"):
        return "right_hand"
    return None


def get_shield_mitigation(is_magical):
    """Calculates passive damage reduction from shields held in left or right hand."""
    mit = 0.0
    for hand in (state["left_hand"], state["right_hand"]):
        if hand and hand.item_class == "SHIELD":
            mit += hand.mag_block if is_magical else hand.phys_block
    return min(0.80, mit)


def save_game(slot_name=""):
    path = _get_save_path(slot_name)
    state["floors"][state["level_idx"]] = {
        "level": state["level"],
        "floor_items": state["floor_items"],
        "monsters": state["monsters"],
    }
    floors_ser = {}
    for idx, fdata in state["floors"].items():
        floors_ser[str(idx)] = {
            "floor_items": {f"{x},{y}": [i.to_dict() for i in items] for (x, y), items in fdata["floor_items"].items()},
            "monsters": [m.to_dict() for m in fdata["monsters"]],
        }
    active_idx = state["backpack"].index(state["active_torch"]) if state["active_torch"] in state["backpack"] else -1
    payload = {
        "level_idx": state["level_idx"],
        "px": state["px"],
        "py": state["py"],
        "pdir": state["pdir"],
        "left_hand": state["left_hand"].to_dict() if state["left_hand"] else None,
        "right_hand": state["right_hand"].to_dict() if state["right_hand"] else None,
        "backpack": [i.to_dict() for i in state["backpack"]],
        "active_torch_idx": active_idx,
        "vitals": state["vitals"].__dict__.copy(),
        "floors": floors_ser,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return os.path.basename(path)


def load_game(slot_name=""):
    global state
    path = _get_save_path(slot_name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    new_state = create_new_game()
    new_state["floors"] = {}
    for idx_str, fdata in payload["floors"].items():
        idx = int(idx_str)
        lvl = DungeonLevel(level_num=idx)
        f_items = {}
        for coord_str, item_list in fdata["floor_items"].items():
            cx, cy = map(int, coord_str.split(","))
            f_items[(cx, cy)] = [GameItem.from_dict(d) for d in item_list]
        mons = [Monster.from_dict(md) for md in fdata["monsters"]]
        new_state["floors"][idx] = {"level": lvl, "floor_items": f_items, "monsters": mons}

    cur_idx = payload["level_idx"]
    cur_floor = new_state["floors"][cur_idx]
    new_state["level_idx"] = cur_idx
    new_state["level"] = cur_floor["level"]
    new_state["floor_items"] = cur_floor["floor_items"]
    new_state["monsters"] = cur_floor["monsters"]
    new_state["px"] = payload["px"]
    new_state["py"] = payload["py"]
    new_state["pdir"] = payload["pdir"]
    new_state["left_hand"] = GameItem.from_dict(payload["left_hand"]) if payload["left_hand"] else None
    new_state["right_hand"] = GameItem.from_dict(payload["right_hand"]) if payload["right_hand"] else None
    new_state["backpack"] = [GameItem.from_dict(d) for d in payload["backpack"]]
    t_idx = payload["active_torch_idx"]
    new_state["active_torch"] = new_state["backpack"][t_idx] if 0 <= t_idx < len(new_state["backpack"]) else None
    new_state["vitals"].__dict__.update(payload["vitals"])
    state = new_state
    recalc_weight()
    return os.path.basename(path)


def update_monsters(dt):
    vitals = state["vitals"]
    if vitals.dead or state.get("victory"):
        return

    px, py, pdir = state["px"], state["py"], state["pdir"]
    level = state["level"]
    monsters = state["monsters"]

    for m in monsters:
        if not m.alive:
            continue

        dist = abs(m.x - px) + abs(m.y - py)
        m.sound_timer -= dt
        if m.sound_timer <= 0:
            m.sound_timer = random.uniform(2.8, 5.5)
            if 0 < dist <= 6:
                sound.play_spatial_monster(m.shape, m.x, m.y, px, py, pdir)
                if dist <= 4:
                    loudness = "LOUD" if dist <= 2 else "FAINT"
                    state["status"] = f"[{loudness} {m.sound_cue} NEARBY!]"

        if (m.x, m.y) == (px, py):
            m.atk_timer -= dt
            if m.atk_timer <= 0:
                m.atk_timer = m.atk_interval
                mit = get_shield_mitigation(m.is_magical)
                raw_shock = m.atk * (1.0 - mit) * (100.0 / max(50.0, float(vitals.strength)))
                vitals.add_exertion(raw_shock)
                sound.play("PLAYER_HIT")
                if vitals.dead:
                    state["status"] = f"SLAIN BY A {m.name}! YOUR HEART STOPPED!"
                    return
                elif mit > 0:
                    state["status"] = f"SHIELD DEFLECTS BLOW FROM {m.name}!"
                else:
                    state["status"] = f"THE {m.name} STRIKES YOU! YOUR HEART RACES!"
        else:
            m.move_timer -= dt
            if m.move_timer <= 0:
                m.move_timer = m.move_interval
                room_loot = state["floor_items"].get((m.x, m.y), [])
                if m.can_loot and room_loot:
                    stolen = room_loot.pop(0)
                    m.held_items.append(stolen)
                elif m.can_see_player(level, px, py):
                    m.step_toward_player(level, px, py, monsters)
                else:
                    m.wander(level, monsters)
                if abs(m.x - px) + abs(m.y - py) <= 5:
                    sound.play_spatial_monster(m.shape, m.x, m.y, px, py, pdir)


def execute_command(cmd):
    global state, gfx_mode
    tokens = cmd.strip().upper().split()
    if not tokens:
        return
    verb = tokens[0]
    arg1 = tokens[1] if len(tokens) > 1 else ""
    rest = tokens[2:]

    vitals = state["vitals"]

    if verb == "RESTART":
        state = create_new_game()
        return
    if verb == "QUIT":
        pygame.quit()
        sys.exit()
    if verb == "GFX":
        order = ["MODERN", "HD", "WIREFRAME"]
        gfx_mode = order[(order.index(gfx_mode) + 1) % len(order)]
        state["status"] = f"GRAPHICS MODE: {gfx_mode}."
        return
    if verb == "MUTE":
        sound.enabled = not sound.enabled
        state["status"] = f"AUDIO {'ENABLED' if sound.enabled else 'MUTED'}."
        return
    if verb == "ZSAVE":
        try:
            fname = save_game(arg1)
            sound.play("REVEAL", 0.5)
            state["status"] = f"SAVED TO saves/{fname}."
        except Exception as exc:
            state["status"] = f"SAVE ERROR: {exc}"
        return
    if verb == "ZLOAD":
        try:
            fname = load_game(arg1)
            if fname:
                sound.play("REVEAL", 0.5)
                state["status"] = f"LOADED saves/{fname} (FLOOR {state['level_idx'] + 1})."
            else:
                state["status"] = "NO SAVE FILE FOUND IN saves/."
        except Exception as exc:
            state["status"] = f"LOAD ERROR: {exc}"
        return

    if vitals.dead or vitals.fainted or state.get("victory"):
        return

    # --- CLIMB UP / DOWN ---
    if verb in ("C", "CLIMB"):
        vert = state["level"].verticals.get((state["px"], state["py"]))
        if arg1 in ("D", "DOWN"):
            if vert and vert.get("down") and state["level_idx"] < 4:
                switch_floor(state["level_idx"] + 1)
                vitals.add_exertion(8.0)
                sound.play("STEP")
                state["status"] = f"DESCENDED TO FLOOR {state['level_idx'] + 1}."
            else:
                state["status"] = "NO PIT OR LADDER GOING DOWN HERE."
        elif arg1 in ("U", "UP"):
            if vert and vert.get("up") == "LADDER" and state["level_idx"] > 0:
                switch_floor(state["level_idx"] - 1)
                vitals.add_exertion(12.0)
                sound.play("STEP")
                state["status"] = f"CLIMBED LADDER TO FLOOR {state['level_idx'] + 1}."
            elif vert and vert.get("up") == "HOLE":
                state["status"] = "THE CEILING SHAFT IS TOO HIGH WITHOUT A LADDER!"
            else:
                state["status"] = "NO LADDER GOING UP HERE."
        else:
            state["status"] = "??? (CLIMB UP OR CLIMB DOWN)"

    # --- INCANT <WORD> ---
    elif verb in ("I", "INCANT"):
        if not arg1:
            state["status"] = "??? (SPEAK AN INCANTATION WORD)"
            return
        held_rings = [h for h in (state["left_hand"], state["right_hand"]) if h and h.item_class == "RING"]
        ring = next((r for r in held_rings if r.revealed and r.incant_word == arg1 and r.charges > 0), None)
        if not ring:
            ring = next((r for r in state["backpack"] if r.item_class == "RING" and r.revealed and r.incant_word == arg1 and r.charges > 0), None)

        if not ring:
            vitals.add_exertion(5.0)
            state["status"] = f"YOU SPEAK '{arg1}', BUT NOTHING ANSWERS..."
            return

        if ring.incant_word == "AETHER":
            sound.play("REVEAL")
            state["victory"] = True
            state["status"] = "AETHER RESONATES! THE DUNGEON CURSE IS BROKEN!"
            return

        ring.incanted = True
        vitals.add_exertion(10.0)
        sound.play("REVEAL")
        state["status"] = f"THE {ring.proper_name} RING BLAZES WITH ARCANE POWER! ({ring.charges} CHARGES)"

    elif verb in ("E", "EXAMINE"):
        state["view_mode"] = "EXAMINE"
        state["status"] = "EXAMINING ROOM & BACKPACK. PRESS TAB OR TYPE 'LOOK' TO RETURN."

    elif verb in ("L", "LOOK"):
        state["view_mode"] = "3D"
        state["status"] = f"FLOOR {state['level_idx'] + 1} - LOOKING {DIR_NAMES[state['pdir']]}."

    elif verb in ("P", "PULL"):
        hand_key = parse_hand(arg1)
        if not hand_key or not rest or state[hand_key] is not None:
            state["status"] = "??? (HAND MUST BE EMPTY: PULL LEFT/RIGHT <ITEM>)"
            return
        match = next((item for item in state["backpack"] if item.matches_query(rest)), None)
        if not match:
            state["status"] = "??? (ITEM NOT IN BACKPACK)"
            return
        state["backpack"].remove(match)
        state[hand_key] = match
        if match is state["active_torch"]:
            match.is_lit = False
            state["active_torch"] = None
            state["status"] = f"PULLED {match.display_name} (EXTINGUISHED TO SAVE FUEL)."
        else:
            state["status"] = f"PULLED {match.display_name}."

    elif verb in ("S", "STOW"):
        hand_key = parse_hand(arg1)
        if not hand_key or state[hand_key] is None:
            state["status"] = "??? (NOTHING IN THAT HAND TO STOW)"
            return
        item = state[hand_key]
        state[hand_key] = None
        state["backpack"].insert(0, item)
        state["status"] = f"STOWED {item.display_name}."

    elif verb in ("G", "GET"):
        hand_key = parse_hand(arg1)
        if not hand_key or not rest or state[hand_key] is not None:
            state["status"] = "??? (HAND MUST BE EMPTY: GET LEFT/RIGHT <ITEM>)"
            return
        pos = (state["px"], state["py"])
        room_list = state["floor_items"].get(pos, [])
        match = next((item for item in room_list if item.matches_query(rest)), None)
        if not match:
            state["status"] = "??? (ITEM NOT ON FLOOR)"
            return
        room_list.remove(match)
        state[hand_key] = match
        recalc_weight()
        sound.play("STEP", 0.4)
        state["status"] = f"PICKED UP {match.display_name}."

    elif verb in ("D", "DROP"):
        hand_key = parse_hand(arg1)
        if not hand_key or state[hand_key] is None:
            state["status"] = "??? (NOTHING IN THAT HAND TO DROP)"
            return
        item = state[hand_key]
        state[hand_key] = None
        pos = (state["px"], state["py"])
        state["floor_items"].setdefault(pos, []).append(item)
        recalc_weight()
        sound.play("STEP", 0.4)
        state["status"] = f"DROPPED {item.display_name}."

    elif verb in ("A", "ATTACK"):
        hand_key = parse_hand(arg1)
        if not hand_key:
            state["status"] = "??? (ATTACK LEFT OR ATTACK RIGHT)"
            return
        weapon = state[hand_key]

        is_ring_blast = bool(weapon and weapon.item_class == "RING" and weapon.incanted and weapon.charges > 0)
        swing_cost = weapon.swing_exertion if weapon else 3.0
        base_dmg = weapon.damage if is_ring_blast else (4 if (weapon and weapon.item_class == "RING") else (weapon.damage if weapon else 4))
        vitals.add_exertion(swing_cost)

        if is_ring_blast:
            weapon.charges -= 1
            if weapon.charges <= 0:
                weapon.incanted = False
                weapon.proper_name = "GOLD"
                weapon.is_magical = False

        dx, dy = DIRS[state["pdir"]]
        front_pos = (state["px"] + dx, state["py"] + dy)
        target = next((m for m in state["monsters"] if m.alive and (m.x, m.y) == (state["px"], state["py"])), None)
        if not target and state["level"].grid[state["py"]][state["px"]][state["pdir"]] in (OPEN, DOOR, MAGIC):
            target = next((m for m in state["monsters"] if m.alive and (m.x, m.y) == front_pos), None)

        if not target:
            sound.play("REVEAL" if is_ring_blast else "SWING")
            state["status"] = f"{'UNLEASHED MAGIC BLAST' if is_ring_blast else 'SWUNG'} AT EMPTY AIR."
            return

        lit = state["active_torch"] is not None and state["active_torch"].is_lit
        hit_chance = 0.95 if is_ring_blast else (0.85 if lit else 0.45)
        if random.random() > hit_chance:
            sound.play("SWING")
            state["status"] = f"MISSED THE {target.name}!"
            return

        if target.ring_only and not is_ring_blast:
            sound.play("SWING")
            state["status"] = f"PHYSICAL WEAPONS BOUNCE OFF THE {target.name}! USE MAGIC!"
            return

        if target.is_magical and not is_ring_blast and (not weapon or not weapon.is_magical):
            sound.play("SWING")
            state["status"] = f"YOUR WEAPON PASSES HARMLESSLY THROUGH THE {target.name}!"
            return

        dealt = base_dmg if is_ring_blast else int(base_dmg * (vitals.strength / 100.0) * (1.0 - target.phys_block))
        target.hp -= max(1, dealt)
        if target.hp <= 0:
            target.alive = False
            sound.play("KILL")
            gained_str = max(6, target.max_hp // 4)
            vitals.strength += gained_str
            if target.held_items:
                state["floor_items"].setdefault((target.x, target.y), []).extend(target.held_items)

            if target.name == "DOPPELGANGER" and state["level_idx"] == 2:
                state["backpack"] = []
                if state["active_torch"]:
                    state["active_torch"].is_lit = False
                    state["active_torch"] = None
                switch_floor(3)
                recalc_weight()
                state["status"] = "DOPPELGANGER SHATTERS! WARPED TO FLOOR 4 WITH ONLY HELD ITEMS!"
            else:
                state["status"] = f"!!! YOU VANQUISHED THE {target.name}! (+STRENGTH)"
        else:
            sound.play("HIT")
            state["status"] = f"!!! HIT THE {target.name}!"

    elif verb in ("U", "USE"):
        hand_key = parse_hand(arg1)
        if not hand_key or state[hand_key] is None:
            state["status"] = "??? (NOTHING IN THAT HAND TO USE)"
            return
        item = state[hand_key]
        if item.item_class == "TORCH":
            if item.minutes_left <= 0 or item.proper_name == "DEAD":
                state["status"] = "THAT TORCH IS COMPLETELY BURNED OUT!"
                return
            if state["active_torch"]:
                state["active_torch"].is_lit = False
            item.is_lit = True
            state["active_torch"] = item
            state[hand_key] = None
            state["backpack"].insert(0, item)
            state["view_mode"] = "3D"
            sound.play("TORCH_LIGHT")
            state["status"] = f"LIT {item.display_name}!"
        elif item.item_class == "FLASK":
            if item.proper_name == "EMPTY":
                state["status"] = "THE FLASK IS EMPTY."
                return
            item.revealed = True
            sound.play("FLASK")
            if item.proper_name == "HALE":
                vitals.exertion = 0.0
                vitals._recalculate_bpm()
                state["status"] = "DRANK HALE FLASK! YOUR HEART RATE CALMS IMMEDIATELY."
            elif item.proper_name == "THEWS":
                vitals.strength += 60
                vitals.exertion = max(0.0, vitals.exertion - 12.0)
                vitals._recalculate_bpm()
                state["status"] = "DRANK THEWS FLASK! SURGING STRENGTH FLOWS THROUGH YOU."
            elif item.proper_name == "ABYE":
                vitals.add_exertion(vitals.strength * 0.85)
                state["status"] = "DRANK ABYE FLASK! AGONIZING EXERTION RACKS YOUR CHEST!"
            item.proper_name = "EMPTY"
        elif item.item_class == "SCROLL":
            if not item.revealed:
                state["status"] = "MUST REVEAL SCROLL BEFORE USING IT!"
            elif item.proper_name == "SEER":
                sound.play("REVEAL")
                state["view_mode"] = "MAP"
                state["status"] = "THE SEER SCROLL REVEALS WALLS & CREATURES!"
            elif item.proper_name == "VISION":
                sound.play("REVEAL")
                state["view_mode"] = "VISION_MAP"
                state["status"] = "THE VISION SCROLL REVEALS SHAFTS, LADDERS & CREATURES!"
        else:
            state["status"] = f"CANNOT USE {item.display_name} THAT WAY."

    elif verb in ("R", "REVEAL"):
        hand_key = parse_hand(arg1)
        if not hand_key or state[hand_key] is None:
            state["status"] = "??? (NOTHING IN THAT HAND TO REVEAL)"
            return
        item = state[hand_key]
        if item.revealed:
            state["status"] = f"ALREADY REVEALED: {item.display_name}."
        elif vitals.strength >= item.reveal_req:
            item.revealed = True
            sound.play("REVEAL")
            extra = f" (WORD: {item.incant_word})" if item.incant_word else ""
            state["status"] = f"REVEALED: {item.display_name}!{extra}"
        else:
            state["status"] = "NOT STRONG ENOUGH TO REVEAL THIS ITEM YET."

    elif verb in ("M", "MOVE"):
        state["view_mode"] = "3D"
        move_dir = state["pdir"]
        if arg1 in ("B", "BACK"):
            move_dir = (state["pdir"] + 2) % 4
        elif arg1 in ("L", "LEFT"):
            move_dir = (state["pdir"] - 1) % 4
        elif arg1 in ("R", "RIGHT"):
            move_dir = (state["pdir"] + 1) % 4

        wall = state["level"].grid[state["py"]][state["px"]][move_dir]
        if wall in (OPEN, DOOR, MAGIC):
            dx, dy = DIRS[move_dir]
            state["px"] += dx
            state["py"] += dy
            move_cost = 4.0 + (state["weight"] * 0.14)
            vitals.add_exertion(move_cost)
            sound.play("STEP")
            here = state["floor_items"].get((state["px"], state["py"]), [])
            vert = state["level"].verticals.get((state["px"], state["py"]))
            notes = []
            if here:
                notes.append(f"{len(here)} ITEM(S)")
            if vert:
                if vert.get("down"):
                    notes.append(f"{vert['down']} DOWN")
                if vert.get("up"):
                    notes.append(f"{vert['up']} UP")
            note_str = f" [{' | '.join(notes)}]" if notes else ""
            state["status"] = f"FL {state['level_idx'] + 1} ({state['px']},{state['py']}) {DIR_NAMES[state['pdir']]}{note_str}"
        else:
            vitals.add_exertion(2.0)
            sound.play("WALL_THUD")
            state["status"] = "THUD! SOLID STONE WALL."

    elif verb in ("T", "TURN"):
        state["view_mode"] = "3D"
        if arg1 in ("L", "LEFT"):
            state["pdir"] = (state["pdir"] - 1) % 4
        elif arg1 in ("R", "RIGHT"):
            state["pdir"] = (state["pdir"] + 1) % 4
        elif arg1 in ("A", "AROUND"):
            state["pdir"] = (state["pdir"] + 2) % 4
        sound.play("STEP", 0.3)
        state["status"] = f"FACING {DIR_NAMES[state['pdir']]}."

    elif verb == "LEVEL" and arg1.isdigit():
        lvl_idx = max(0, min(4, int(arg1) - 1))
        switch_floor(lvl_idx)
        sound.play("REVEAL")
        state["status"] = f"WARPED TO FLOOR {lvl_idx + 1}!"

    elif verb == "MAP":
        state["view_mode"] = "VISION_MAP" if state["view_mode"] not in ("MAP", "VISION_MAP") else "3D"

    elif verb == "TIME" and arg1.isdigit():
        state["time_scale"] = max(1.0, min(60.0, float(arg1)))
        state["status"] = f"CLOCK SPEED SET TO {int(state['time_scale'])}X."

    else:
        state["status"] = f"??? ({cmd})"


clock = pygame.time.Clock()
beat_phase = 0.0
beat_triggered = False

while True:
    dt = clock.tick(60) / 1000.0
    vitals = state["vitals"]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        controls.process_event(event, state, execute_command)

    if not vitals.fainted and not vitals.dead and not state.get("victory"):
        controls.update_analog_sticks(dt, execute_command)

    update_monsters(dt)

    vital_event = vitals.update(dt, state["active_torch"], state["time_scale"])
    if vital_event:
        state["status"] = vital_event
        if vitals.fainted:
            state["cmd_buffer"] = ""
            controls.typing_mode = False

    if not vitals.dead:
        beats_per_sec = vitals.current_bpm / 60.0
        prev_phase = beat_phase
        beat_phase = (beat_phase + dt * beats_per_sec) % 1.0
        if beat_phase < prev_phase:
            beat_triggered = False
        if beat_phase >= 0.10 and not beat_triggered:
            sound.play_heartbeat(vitals.current_bpm, vitals.faint_threshold)
            beat_triggered = True

        lub = math.exp(-((beat_phase - 0.15) ** 2) / 0.003)
        dub = 0.65 * math.exp(-((beat_phase - 0.35) ** 2) / 0.004)
        state["pulse"] = min(1.0, lub + dub)
    else:
        state["pulse"] = 0.0

    display_state = dict(state)
    if not controls.typing_mode and not vitals.fainted and not vitals.dead and not state.get("victory"):
        display_state["cmd_buffer"] = "[WASD / PAD ACTIVE - PRESS ENTER TO TYPE]"

    if gfx_mode == "MODERN":
        gl_renderer.render_frame(display_state)
    else:
        active_2d = hd_renderer if gfx_mode == "HD" else wire_renderer
        active_2d.render_frame(display_state)
        gl_renderer.ctx.clear(0.0, 0.0, 0.0, 1.0)
        gl_renderer.blit_pygame_surface(offscreen_2d)
        pygame.display.flip()