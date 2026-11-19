# Cinders & Echo

**Cinders & Echo** is a first-person, grid-based survival dungeon crawler inspired by classic 1980s real-time vector crawlers. Built from the ground up in Python (`pygame-ce`), the project first achieves complete gameplay parity with the classic formula—real-time heartbeat exertion, finite torchlight, spatial stereo creature tracking, vertical shaft traversal, and arcane ring incantations—before evolving into a modernized spiritual successor featuring **Gritty Dark-Fantasy Painted** visuals, tactile mouse/gamepad controls, and an interactive UI.

---

## Project Vision & Roadmap

### Phase 1: Complete Core Engine (Current Baseline)
* **5-Level Procedural Labyrinth:** Deterministic 32×32 dungeon floors connected by floor pits, ceiling hatches, and two-way ladders (`CLIMB UP` / `CLIMB DOWN`).
* **Real-Time Heartbeat & Exertion System:** Every step, weapon swing, heavy pack load, and monster blow drives your heart rate higher—pushing too hard causes exhaustion fainting, and reaching cardiac limit ends the run.
* **Finite Light & Perception:** Torches (`PINE`, `LUNAR`, `SOLAR`) burn down in real time; magical light reveals hidden arcane passages and ethereal creatures.
* **12-Creature Bestiary & Boss Progression:** From skittering Spiders and venomous Scorpions to Shield Knights, Wraiths, the Level 3 Shadow Doppelganger, and the Level 5 Arch-Warlock.
* **Arcane Rings & Incantations:** Uncover and awaken elemental rings (`IGNIS`, `GLACIES`, `FULGUR`, and `AETHER`) to unleash magical blasts and break the dungeon curse.
* **Spatial Stereo Audio:** Procedural 16-bit stereo sound engine that syncs the *lub-dub* heartbeat to your live BPM and pans monster footsteps/cries across left and right channels relative to your facing direction.
* **Dual Render Modes & Hybrid Controls:** Instant hot-swapping (`GFX`) between **HD 2.5D Textured** corridors and **Classic Wireframe** vectors, playable via WASD/mouse, USB/Bluetooth gamepads, or classic typed commands.
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