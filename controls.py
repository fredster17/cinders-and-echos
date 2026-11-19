import pygame


class InputController:
    def __init__(self):
        pygame.joystick.init()
        self.joysticks = []
        self.typing_mode = False
        self.stick_cooldown = 0.0
        self.refresh_controllers()

    def refresh_controllers(self):
        """Detects plugged-in USB/Bluetooth gamepads."""
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self.joysticks.append(joy)

    @property
    def controller_name(self):
        return self.joysticks[0].get_name() if self.joysticks else None

    def process_event(self, event, state, execute_fn):
        """
        Translates keyboard hotkeys, mouse clicks, and gamepad inputs into game commands.
        Pressing ENTER toggles Typing Mode so WASD doesn't fire while typing text commands.
        """
        if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self.refresh_controllers()
            return

        # --- MOUSE CLICKS (Left/Right Hand Attacks in 3D View) ---
        if event.type == pygame.MOUSEBUTTONDOWN and not self.typing_mode:
            if state["view_mode"] == "3D":
                if event.button == 1:      # Left Click -> Attack Left Hand
                    execute_fn("ATTACK LEFT")
                elif event.button == 3:    # Right Click -> Attack Right Hand
                    execute_fn("ATTACK RIGHT")
            return

        # --- KEYBOARD INPUT ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.typing_mode:
                    if state["cmd_buffer"].strip():
                        execute_fn(state["cmd_buffer"])
                    state["cmd_buffer"] = ""
                    self.typing_mode = False
                else:
                    self.typing_mode = True
                    state["cmd_buffer"] = ""
                return

            if event.key == pygame.K_ESCAPE and self.typing_mode:
                state["cmd_buffer"] = ""
                self.typing_mode = False
                return

            if self.typing_mode:
                if event.key == pygame.K_BACKSPACE:
                    state["cmd_buffer"] = state["cmd_buffer"][:-1]
                elif event.unicode.isprintable():
                    state["cmd_buffer"] += event.unicode
                return

            # --- MODERN WASD / HOTKEY CONTROLS ---
            key = event.key
            if key in (pygame.K_w, pygame.K_UP):
                execute_fn("MOVE")
            elif key in (pygame.K_s, pygame.K_DOWN):
                execute_fn("MOVE BACK")
            elif key in (pygame.K_a, pygame.K_LEFT):
                execute_fn("TURN LEFT")
            elif key in (pygame.K_d, pygame.K_RIGHT):
                execute_fn("TURN RIGHT")
            elif key == pygame.K_q:
                execute_fn("MOVE LEFT")
            elif key == pygame.K_e:
                execute_fn("MOVE RIGHT")
            elif key == pygame.K_TAB:
                execute_fn("LOOK" if state["view_mode"] == "EXAMINE" else "EXAMINE")
            elif key == pygame.K_m:
                execute_fn("MAP")
            elif key == pygame.K_1:
                execute_fn("USE LEFT")
            elif key == pygame.K_2:
                execute_fn("USE RIGHT")

        # --- GAMEPAD D-PAD & FACE BUTTONS ---
        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            if hy == 1:
                execute_fn("MOVE")
            elif hy == -1:
                execute_fn("MOVE BACK")
            elif hx == -1:
                execute_fn("TURN LEFT")
            elif hx == 1:
                execute_fn("TURN RIGHT")

        elif event.type == pygame.JOYBUTTONDOWN:
            btn = event.button
            if btn == 2:      # X / Square -> Attack Left
                execute_fn("ATTACK LEFT")
            elif btn == 1:    # B / Circle -> Attack Right
                execute_fn("ATTACK RIGHT")
            elif btn == 0:    # A / Cross -> Move Forward
                execute_fn("MOVE")
            elif btn == 3:    # Y / Triangle -> Toggle Examine / Look
                execute_fn("LOOK" if state["view_mode"] == "EXAMINE" else "EXAMINE")
            elif btn == 4:    # LB -> Sidestep Left
                execute_fn("MOVE LEFT")
            elif btn == 5:    # RB -> Sidestep Right
                execute_fn("MOVE RIGHT")
            elif btn == 6:    # Back / Select -> Toggle Map
                execute_fn("MAP")

    def update_analog_sticks(self, dt, execute_fn):
        """Polls left analog stick & triggers smoothly with step repeat delay."""
        if self.stick_cooldown > 0:
            self.stick_cooldown -= dt
            return

        for joy in self.joysticks:
            if joy.get_numaxes() >= 2:
                ax_x = joy.get_axis(0)
                ax_y = joy.get_axis(1)
                deadzone = 0.55

                if ax_y < -deadzone:
                    execute_fn("MOVE")
                    self.stick_cooldown = 0.24
                    return
                elif ax_y > deadzone:
                    execute_fn("MOVE BACK")
                    self.stick_cooldown = 0.24
                    return
                elif ax_x < -deadzone:
                    execute_fn("TURN LEFT")
                    self.stick_cooldown = 0.24
                    return
                elif ax_x > deadzone:
                    execute_fn("TURN RIGHT")
                    self.stick_cooldown = 0.24
                    return

            if joy.get_numaxes() >= 6:
                lt = joy.get_axis(4)
                rt = joy.get_axis(5)
                if lt > 0.5:
                    execute_fn("ATTACK LEFT")
                    self.stick_cooldown = 0.30
                    return
                elif rt > 0.5:
                    execute_fn("ATTACK RIGHT")
                    self.stick_cooldown = 0.30
                    return