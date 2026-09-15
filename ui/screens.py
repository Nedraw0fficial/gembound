import pygame
import config
from ui.widgets import Button, TextInput
from network.discovery import Listener
import time

JOIN_MODE_LIST = "list"
JOIN_MODE_PASSWORD = "password"

SCREEN_MENU = "menu"
SCREEN_CREATE_LOBBY = "create_lobby"
SCREEN_JOIN = "join"
SCREEN_IN_GAME = "in_game"
SCREEN_OPTIONS = "options"


class MenuScreen:
    def __init__(self, font, title_font):
        self.font = font
        self.title_font = title_font
        center_x = config.SCREEN_WIDTH // 2

        self.pseudo_input = TextInput(center_x - 120, 220, 240, 36, font, placeholder="Pseudo (optionnel)")
        self.create_button = Button(center_x - 120, 280, 240, 44, "Create Lobby", font)
        self.join_button = Button(center_x - 120, 336, 240, 44, "Join Lobby", font)
        self.options_button = Button(center_x - 120, 392, 240, 44, "Options", font)

    def handle_event(self, event):
        self.pseudo_input.handle_event(event)
        if self.create_button.handle_event(event):
            return ("create", self.pseudo_input.text.strip() or "Joueur")
        if self.join_button.handle_event(event):
            return ("join", self.pseudo_input.text.strip() or "Joueur")
        if self.options_button.handle_event(event):
            return ("options", None)
        return None

    def update(self, mouse_pos):
        self.create_button.update_hover(mouse_pos)
        self.join_button.update_hover(mouse_pos)
        self.options_button.update_hover(mouse_pos)

    def draw(self, screen):
        title = self.title_font.render(config.GAME_TITLE, True, (255, 255, 255))
        screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        self.pseudo_input.draw(screen)
        self.create_button.draw(screen)
        self.join_button.draw(screen)
        self.options_button.draw(screen)


class CreateLobbyScreen:
    def __init__(self, font):
        self.font = font
        center_x = config.SCREEN_WIDTH // 2

        self.name_input = TextInput(center_x - 120, 160, 240, 36, font, placeholder="Nom du lobby")
        self.seed_input = TextInput(center_x - 120, 208, 240, 36, font, placeholder="Seed (optionnel)")
        self.password_input = TextInput(center_x - 120, 256, 240, 36, font, placeholder="Mot de passe (optionnel)")

        self.max_players = 4
        self.minus_button = Button(center_x - 120, 304, 44, 40, "-", font)
        self.plus_button = Button(center_x + 76, 304, 44, 40, "+", font)

        self.is_lan = False
        self.lan_toggle_button = Button(center_x - 120, 360, 240, 44, self._lan_label(), font)

        self.create_button = Button(center_x - 120, 420, 240, 44, "Créer", font)

    def _lan_label(self):
        return f"Mode : {'LAN' if self.is_lan else 'Serveur en ligne'}"

    def handle_event(self, event):
        self.name_input.handle_event(event)
        self.seed_input.handle_event(event)
        self.password_input.handle_event(event)

        if self.minus_button.handle_event(event):
            self.max_players = max(1, self.max_players - 1)
        if self.plus_button.handle_event(event):
            self.max_players = min(4, self.max_players + 1)

        if self.lan_toggle_button.handle_event(event):
            self.is_lan = not self.is_lan
            self.lan_toggle_button.text = self._lan_label()

        if self.create_button.handle_event(event):
            seed_text = self.seed_input.text.strip()
            return {
                "name": self.name_input.text.strip() or "Sans nom",
                "seed": seed_text if seed_text else None,
                "max_players": self.max_players,
                "password": "" if self.is_lan else self.password_input.text.strip(),
                "is_lan": self.is_lan,
            }
        return None

    def update(self, mouse_pos):
        self.minus_button.update_hover(mouse_pos)
        self.plus_button.update_hover(mouse_pos)
        self.lan_toggle_button.update_hover(mouse_pos)
        self.create_button.update_hover(mouse_pos)

    def draw(self, screen):
        self.name_input.draw(screen)
        self.seed_input.draw(screen)

        if not self.is_lan:
            self.password_input.draw(screen)

        self.minus_button.draw(screen)
        self.plus_button.draw(screen)
        count_text = self.font.render(f"Joueurs max : {self.max_players}", True, (255, 255, 255))
        screen.blit(count_text, (config.SCREEN_WIDTH // 2 - count_text.get_width() // 2, 310))

        self.lan_toggle_button.draw(screen)
        self.create_button.draw(screen)


import time

JOIN_MODE_LIST = "list"
JOIN_MODE_PASSWORD = "password"


class JoinScreen:
    def __init__(self, font, pseudo):
        self.font = font
        self.pseudo = pseudo

        self.listener = Listener()

        from network.online_client import OnlineClient
        try:
            self.directory_client = OnlineClient(pseudo)
            self.directory_client.request_lobby_list()
        except OSError:
            self.directory_client = None

        self._last_request_time = time.monotonic()

        self.game_buttons = {}
        self.visible_entries = {}

        self.mode = JOIN_MODE_LIST
        self.password_target = None  # lobby_id en attente de mot de passe
        center_x = config.SCREEN_WIDTH // 2
        self.password_input = TextInput(center_x - 120, 300, 240, 36, font, placeholder="Mot de passe")
        self.password_confirm_button = Button(center_x - 120, 344, 240, 44, "Rejoindre", font)
        self.password_cancel_button = Button(center_x - 120, 396, 240, 40, "Annuler", font)

    def _label_for_lan(self, game):
        full = game["current_players"] >= game["max_players"]
        label = f"{game['pseudo']} — {game['save_name']} ({game['current_players']}/{game['max_players']})"
        label += "  [LAN]"
        if full:
            label += " [complet]"
        return label

    def _label_for_online(self, lobby):
        full = lobby["current_players"] >= lobby["max_players"]
        label = f"{lobby['creator_pseudo']} — {lobby['name']} ({lobby['current_players']}/{lobby['max_players']})"
        if lobby["has_password"]:
            label += " [pw]"
        if full:
            label += " FULL!"
        return label

    def _sync_entries(self):
        self.listener.poll()
        if self.directory_client is not None:
            self.directory_client.poll_network()
            if time.monotonic() - self._last_request_time > 1.5:
                self.directory_client.request_lobby_list()
                self._last_request_time = time.monotonic()

        entries = {}
        for ip, game in self.listener.games.items():
            if game["max_players"] <= 1:
                continue
            entries[("lan", ip)] = ("lan", game, self._label_for_lan(game))

        if self.directory_client is not None:
            for lobby in self.directory_client.lobby_list:
                entries[("online", lobby["id"])] = ("online", lobby, self._label_for_online(lobby))

        center_x = config.SCREEN_WIDTH // 2
        y = 160
        for key in list(self.game_buttons.keys()):
            if key not in entries:
                del self.game_buttons[key]

        for key, (kind, data, label) in sorted(entries.items(), key=lambda kv: kv[1][2]):
            if key in self.game_buttons:
                self.game_buttons[key].text = label
                self.game_buttons[key].rect.topleft = (center_x - 200, y)
            else:
                self.game_buttons[key] = Button(center_x - 200, y, 400, 40, label, self.font)
            y += 48

        self.visible_entries = entries

    def handle_event(self, event):
        if self.mode == JOIN_MODE_PASSWORD:
            self.password_input.handle_event(event)
            if self.password_confirm_button.handle_event(event):
                lobby_id = self.password_target
                password = self.password_input.text
                self.mode = JOIN_MODE_LIST
                self.password_target = None
                return ("online", lobby_id, password)
            if self.password_cancel_button.handle_event(event):
                self.mode = JOIN_MODE_LIST
                self.password_target = None
            return None

        self._sync_entries()
        for key, button in self.game_buttons.items():
            kind, data, label = self.visible_entries[key]
            full = data["current_players"] >= data["max_players"]
            if full:
                continue
            if button.handle_event(event):
                if kind == "lan":
                    return ("lan", data["ip"])
                else:
                    if data["has_password"]:
                        self.mode = JOIN_MODE_PASSWORD
                        self.password_target = data["id"]
                        self.password_input.text = ""
                    else:
                        return ("online", data["id"], "")
        return None

    def update(self, mouse_pos):
        if self.mode == JOIN_MODE_PASSWORD:
            self.password_confirm_button.update_hover(mouse_pos)
            self.password_cancel_button.update_hover(mouse_pos)
            return

        self._sync_entries()
        for key, button in self.game_buttons.items():
            kind, data, label = self.visible_entries[key]
            if data["current_players"] < data["max_players"]:
                button.update_hover(mouse_pos)

    def draw(self, screen):
        if self.mode == JOIN_MODE_PASSWORD:
            prompt = self.font.render("Mot de passe requis :", True, (255, 255, 255))
            screen.blit(prompt, (config.SCREEN_WIDTH // 2 - prompt.get_width() // 2, 260))
            self.password_input.draw(screen)
            self.password_confirm_button.draw(screen)
            self.password_cancel_button.draw(screen)
            return

        if not self.visible_entries:
            text = self.font.render("Recherche de parties...", True, (200, 200, 200))
            screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2, 160))
            return

        for key, button in self.game_buttons.items():
            kind, data, label = self.visible_entries[key]
            full = data["current_players"] >= data["max_players"]
            if full:
                dimmed = button.font.render(button.text, True, (120, 120, 120))
                screen.blit(dimmed, (button.rect.x, button.rect.y + 10))
            else:
                button.draw(screen)

    def close(self):
        self.listener.close()
        if self.directory_client is not None:
            self.directory_client.close()

    def close_lan_listener(self):
        self.listener.close()

class OptionsScreen:
    def __init__(self, font, settings):
        self.font = font
        self.settings = settings
        center_x = config.SCREEN_WIDTH // 2

        self.resolution_index = self._find_resolution_index()
        self.res_minus_button = Button(center_x - 160, 200, 44, 40, "-", font)
        self.res_plus_button = Button(center_x + 116, 200, 44, 40, "+", font)

        self.fullscreen_button = Button(center_x - 120, 260, 240, 44,
                                          self._fullscreen_label(), font)

        self.remap_buttons = {}
        y = 340
        for action in ("up", "down", "left", "right"):
            self.remap_buttons[action] = Button(center_x - 120, y, 240, 40,
                                                  self._keybind_label(action), font)
            y += 48

        self.back_button = Button(center_x - 120, y + 20, 240, 44, "Retour", font)

        self.listening_for = None

    def _find_resolution_index(self):
        from settings import DEFAULT_RESOLUTIONS
        try:
            return DEFAULT_RESOLUTIONS.index(self.settings.resolution)
        except ValueError:
            return 0

    def _fullscreen_label(self):
        return f"Plein écran : {'Oui' if self.settings.fullscreen else 'Non'}"

    def _keybind_label(self, action):
        from settings import DEFAULT_KEYBINDS
        key_names = [pygame.key.name(k).upper() for k in self.settings.keybinds.get(action, [])]
        label = " / ".join(key_names) if key_names else "..."
        action_label = {"up": "Haut", "down": "Bas", "left": "Gauche", "right": "Droite"}[action]
        return f"{action_label} : {label}"

    def handle_event(self, event):
        from settings import DEFAULT_RESOLUTIONS

        if self.listening_for is not None:
            if event.type == pygame.KEYDOWN:
                self.settings.keybinds[self.listening_for] = [event.key]
                self.remap_buttons[self.listening_for].text = self._keybind_label(self.listening_for)
                self.listening_for = None
            return None

        if self.res_minus_button.handle_event(event):
            self.resolution_index = max(0, self.resolution_index - 1)
            self.settings.resolution = DEFAULT_RESOLUTIONS[self.resolution_index]
            return "resolution_changed"

        if self.res_plus_button.handle_event(event):
            self.resolution_index = min(len(DEFAULT_RESOLUTIONS) - 1, self.resolution_index + 1)
            self.settings.resolution = DEFAULT_RESOLUTIONS[self.resolution_index]
            return "resolution_changed"

        if self.fullscreen_button.handle_event(event):
            self.settings.fullscreen = not self.settings.fullscreen
            self.fullscreen_button.text = self._fullscreen_label()
            return "resolution_changed"

        for action, button in self.remap_buttons.items():
            if button.handle_event(event):
                self.listening_for = action
                button.text = "Appuie sur une touche..."

        if self.back_button.handle_event(event):
            return "back"

        return None

    def update(self, mouse_pos):
        self.res_minus_button.update_hover(mouse_pos)
        self.res_plus_button.update_hover(mouse_pos)
        self.fullscreen_button.update_hover(mouse_pos)
        self.back_button.update_hover(mouse_pos)
        for button in self.remap_buttons.values():
            button.update_hover(mouse_pos)

    def draw(self, screen):
        from settings import DEFAULT_RESOLUTIONS

        self.res_minus_button.draw(screen)
        self.res_plus_button.draw(screen)

        res_text = f"{self.settings.resolution[0]} x {self.settings.resolution[1]}"
        res_label = self.font.render(res_text, True, (255, 255, 255))
        screen.blit(res_label, (config.SCREEN_WIDTH // 2 - res_label.get_width() // 2, 210))

        self.fullscreen_button.draw(screen)

        for button in self.remap_buttons.values():
            button.draw(screen)

        self.back_button.draw(screen)