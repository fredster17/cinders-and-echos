# Cinders & Echo

**Cinders & Echo** is a first-person, grid-based survival dungeon crawler inspired by classic 1980s real-time vector crawlers. Built from the ground up in Python (`pygame-ce`), the project first achieves complete gameplay parity with the classic formula—real-time heartbeat exertion, finite torchlight, spatial stereo creature tracking, vertical shaft traversal, and arcane ring incantations—before evolving into a modernized spiritual successor featuring **Gritty Dark-Fantasy Painted** visuals, tactile mouse/gamepad controls, and an interactive UI.

---

## Quick-Start Gameplay & Graphics Toggle

1. **Initiate Controls (Modern vs. Typing Mode):**
   * **Modern Controls (Active by Default):** Use **`W A S D`** (or Arrow keys) to move/turn, **`Q` / `E`** to sidestep, and **Left-Click / Right-Click** to attack with your left or right hand.
   * **Text Command Prompt:** Press **`Enter`** at any time to unlock the command prompt (`> _`) at the bottom of the screen, type your command, and press **`Enter`** again to execute it.
2. **Light Your First Torch:** You spawn in pitch darkness with a **Pine Torch** and **Wooden Sword** in your backpack.
   * Press **`Enter`**, type **`P R T`** (`PULL RIGHT TORCH`), and press **`Enter`**.
   * Press **`Enter`**, type **`U R`** (`USE RIGHT`), and press **`Enter`** (or press **`2`**) to ignite your torch.
3. **Switch Between HD 2.5D Graphics & Classic Wireframe:**
   * Press **`Enter`**, type **`GFX`**, and press **`Enter`** at any time to hot-swap between **HD 2.5D Textured** mode and **Classic Vector Wireframe** mode (type **`GFX`** again to switch back).
4. **Inspect Room Loot, Map & Vertical Shafts:**
   * Press **`Tab`** (or type **`E`**) to open the **Examine** view showing items on the floor and in your backpack; press **`Tab`** (or **`L`**) to return to the 3D view.
   * Press **`M`** (or type **`MAP`**) to toggle the overhead dungeon map.
   * Stand on a floor pit or ladder and type **`C D`** (`CLIMB DOWN`) or **`C U`** (`CLIMB UP`) to traverse between the 5 dungeon levels.

---

## Controls & Commands Reference

### Modern Keyboard, Mouse & Gamepad Controls
| Action | Keyboard / Mouse | USB / Bluetooth Gamepad |
| :--- | :--- | :--- |
| **Move Forward / Back** | `W` / `S` or `Up` / `Down` | Left Stick / D-Pad Up & Down (`A` to step forward) |
| **Turn Left / Right** | `A` / `D` or `Left` / `Right` | Left Stick / D-Pad Left & Right |
| **Sidestep Left / Right** | `Q` / `E` | `LB` / `RB` |
| **Attack Left / Right Hand** | `Left-Click` / `Right-Click` | `X` / `B` or `LT` / `RT` |
| **Use Left / Right Hand Item** | `1` / `2` | — |
| **Examine Room & Backpack** | `Tab` | `Y` |
| **Toggle Overhead Map** | `M` | `Back` / `Select` |
| **Toggle Text Command Prompt** | `Enter` | — |

### Classic Text Commands (Type After Pressing `Enter`)
| Command | Short Form | Description |
| :--- | :--- | :--- |
| `MOVE [BACK\|LEFT\|RIGHT]` | `M`, `M B`, `M L`, `M R` | Step one tile forward, backward, or sideways. |
| `TURN <LEFT\|RIGHT\|AROUND>` | `T L`, `T R`, `T A` | Rotate facing direction 90° or 180°. |
| `CLIMB <UP\|DOWN>` | `C U`, `C D` | Ascend a ladder or descend a floor pit/ladder. |
| `EXAMINE` / `LOOK` | `E` / `L` | Inspect room floor & backpack, or return to 3D view. |
| `GET <L\|R> <ITEM>` | `G L SHIELD`, `G R RING` | Pick up an item from the floor into an empty hand. |
| `DROP <L\|R>` | `D L`, `D R` | Drop a held item onto the dungeon floor. |
| `PULL <L\|R> <ITEM>` | `P L SW`, `P R T` | Pull an item from your backpack into an empty hand. |
| `STOW <L\|R>` | `S L`, `S R` | Store a held item into your backpack. |
| `USE <L\|R>` | `U L`, `U R` | Light a torch, drink a flask, or read a revealed scroll. |
| `REVEAL <L\|R>` | `R L`, `R R` | Identify an item's true name and magic incantation word. |
| `INCANT <WORD>` | `I IGNIS` | Awaken a revealed ring (`IGNIS`, `GLACIES`, `FULGUR`, `AETHER`). |
| `ATTACK <L\|R>` | `A L`, `A R` | Strike or unleash ring magic with your left or right hand. |
| `GFX` | — | Hot-swap between **HD 2.5D Textured** and **Classic Wireframe** modes. |
| `MUTE` | — | Toggle procedural stereo audio and heartbeat sound effects. |
| `MAP` | — | Toggle the overhead dungeon map. |
| `ZSAVE [NAME]` / `ZLOAD [NAME]` | — | Save or load your multi-floor progress in `saves/`. |
| `RESTART` / `QUIT` | — | Start a fresh dungeon run or exit the game. |

---

## Project Vision & Roadmap

### Phase 1: Complete Core Engine (Current Baseline)
* **5-Level Procedural Labyrinth:** Deterministic 32×32 dungeon floors connected by floor pits, ceiling hatches, and two-way ladders.
* **Real-Time Heartbeat & Exertion System:** Every step, weapon swing, heavy pack load, and monster blow drives your heart rate higher—pushing too hard causes exhaustion fainting, and reaching cardiac limit ends the run.
* **Finite Light & Perception:** Torches (`PINE`, `LUNAR`, `SOLAR`) burn down in real time; magical light reveals hidden arcane passages and ethereal creatures.
* **12-Creature Bestiary & Boss Progression:** From skittering Spiders and venomous Scorpions to Shield Knights, Wraiths, the Level 3 Shadow Doppelganger, and the Level 5 Arch-Warlock.
* **Arcane Rings & Incantations:** Uncover and awaken elemental rings (`IGNIS`, `GLACIES`, `FULGUR`, and `AETHER`) to unleash magical blasts and break the dungeon curse.
* **Spatial Stereo Audio:** Procedural 16-bit stereo sound engine that syncs the *lub-dub* heartbeat to your live BPM and pans monster footsteps/cries across left and right channels relative to your facing direction.
* **Multi-Floor Persistence:** Full state save and load support (`ZSAVE` / `ZLOAD`).

### Phase 2: Modern Spiritual Successor (Next Up)
* **Gritty Dark-Fantasy Painted Art Pipeline:** Replacing procedural wall and creature placeholders with hand-painted textures, first-person held torch/weapon overlays, and dynamic flickering torchlight shaders while retaining the classic wireframe toggle.
* **Interactive Mouse & Gamepad UI:** Making the `Tab` (`EXAMINE`) room/backpack view and Left/Right hand HUD slots directly clickable and navigable without needing text commands.
* **Expanded Gameplay Systems:** Evolving combat pacing, environmental storytelling, and modernized quality-of-life mechanics.

---

## Installation & Running

1. **Requirements:** Python 3.10+ and `pygame-ce`
   ```bash
   pip install pygame-ce