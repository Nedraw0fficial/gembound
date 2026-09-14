import pygame
import config
from ui.widgets import Button, TextInput
from network.discovery import Listener

SCREEN_MENU = "menu"
SCREEN_HOST_SETUP = "host_setup"
SCREEN_JOIN = "join"
SCREEN_IN_GAME = "in_game"


class MenuScreen:
    def __init__(self, font, title_font):
        self.font = font
        self.title_font = title_font
        center_x = config.SCREEN_WIDTH // 2

        self.pseudo_input = TextInput(center_x - 120, 220, 240, 36, font, placeholder="Pseudo (optionnel)")
        self.host_button = Button(center_x - 120, 280, 240, 44, "Héberger", font)
        self.join_button = Button(center_x - 120, 336, 240, 44, "Rejoindre", font)

    def handle_event(self, event):
        self.pseudo_input.handle_event(event)
        if self.host_button.handle_event(event):
            return ("host", self.pseudo_input.text.strip() or "Joueur")
        if self.join_button.handle_event(event):
            return ("join", self.pseudo_input.text.strip() or "Joueur")
        return None

    def update(self, mouse_pos):
        self.host_button.update_hover(mouse_pos)
        self.join_button.update_hover(mouse_pos)

    def draw(self, screen):
        title = self.title_font.render(config.GAME_TITLE, True, (255, 255, 255))
        screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        self.pseudo_input.draw(screen)
        self.host_button.draw(screen)
        self.join_button.draw(screen)


class HostSetupScreen:
    def __init__(self, font):
        self.font = font
        center_x = config.SCREEN_WIDTH // 2

        self.seed_input = TextInput(center_x - 120, 180, 240, 36, font, placeholder="Seed (optionnel)")
        self.save_name_input = TextInput(center_x - 120, 240, 240, 36, font, placeholder="Nom de la sauvegarde")

        self.max_players = 4
        self.minus_button = Button(center_x - 120, 300, 44, 40, "-", font)
        self.plus_button = Button(center_x + 76, 300, 44, 40, "+", font)

        self.play_button = Button(center_x - 120, 350, 240, 44, "Jouer", font)

    def handle_event(self, event):
        self.seed_input.handle_event(event)
        self.save_name_input.handle_event(event)

        if self.minus_button.handle_event(event):
            self.max_players = max(1, self.max_players - 1)
        if self.plus_button.handle_event(event):
            self.max_players = min(4, self.max_players + 1)

        if self.play_button.handle_event(event):
            seed_text = self.seed_input.text.strip()
            seed = seed_text if seed_text else None
            save_name = self.save_name_input.text.strip() or "Sans nom"
            return {
                "seed": seed,
                "max_players": self.max_players,
                "save_name": save_name,
            }
        return None

    def update(self, mouse_pos):
        self.minus_button.update_hover(mouse_pos)
        self.plus_button.update_hover(mouse_pos)
        self.play_button.update_hover(mouse_pos)

    def draw(self, screen):
        self.seed_input.draw(screen)
        self.save_name_input.draw(screen)

        self.minus_button.draw(screen)
        self.plus_button.draw(screen)

        count_text = self.font.render(f"Joueurs max : {self.max_players}", True, (255, 255, 255))
        screen.blit(count_text, (config.SCREEN_WIDTH // 2 - count_text.get_width() // 2, 306))

        self.play_button.draw(screen)


class JoinScreen:
    def __init__(self, font):
        self.font = font
        self.listener = Listener()
        self.game_buttons = {}
        self.visible_games = {}

    def _label_for(self, game):
        full = game["current_players"] >= game["max_players"]
        label = f"{game['pseudo']} — {game['save_name']} ({game['current_players']}/{game['max_players']})"
        if full:
            label += " [complet]"
        return label

    def _sync_buttons(self):
        self.listener.poll()
        self.visible_games = {
            ip: g for ip, g in self.listener.games.items()
            if g["max_players"] > 1
        }

        center_x = config.SCREEN_WIDTH // 2
        y = 160

        for ip in list(self.game_buttons.keys()):
            if ip not in self.visible_games:
                del self.game_buttons[ip]

        for ip, game in sorted(self.visible_games.items(), key=lambda item: item[1]["pseudo"]):
            label = self._label_for(game)
            if ip in self.game_buttons:
                self.game_buttons[ip].text = label
                self.game_buttons[ip].rect.topleft = (center_x - 200, y)
            else:
                self.game_buttons[ip] = Button(center_x - 200, y, 400, 40, label, self.font)
            y += 48

    def handle_event(self, event):
        self._sync_buttons()
        for ip, button in self.game_buttons.items():
            game = self.visible_games[ip]
            if game["current_players"] >= game["max_players"]:
                continue
            if button.handle_event(event):
                return ip
        return None

    def update(self, mouse_pos):
        self._sync_buttons()
        for ip, button in self.game_buttons.items():
            if self.visible_games[ip]["current_players"] < self.visible_games[ip]["max_players"]:
                button.update_hover(mouse_pos)

    def draw(self, screen):
        if not self.visible_games:
            text = self.font.render("Recherche de parties sur le réseau...", True, (200, 200, 200))
            screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2, 160))
            return

        for ip, button in self.game_buttons.items():
            game = self.visible_games[ip]
            if game["current_players"] >= game["max_players"]:
                dimmed = button.font.render(button.text, True, (120, 120, 120))
                screen.blit(dimmed, (button.rect.x, button.rect.y + 10))
            else:
                button.draw(screen)

    def close(self):
        self.listener.close()