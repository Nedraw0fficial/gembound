import pygame
import config
from ui.nine_slice import slice_image, render_nine_slice

BUTTON_SPRITE_PATHS = {
    "default": "assets/sprites/ui/button_default.png",
    "hovered": "assets/sprites/ui/button_hovered.png",
    "pressed": "assets/sprites/ui/button_pressed.png",
}

_button_pieces_cache = {}


def _get_button_pieces(state):
    if state not in _button_pieces_cache:
        img = pygame.image.load(BUTTON_SPRITE_PATHS[state]).convert_alpha()
        _button_pieces_cache[state] = slice_image(img)
    return _button_pieces_cache[state]


class Button:
    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.state = "default"

    def handle_event(self, event):
        """Retourne True si le bouton a été cliqué (relâché) sur ce frame."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = "pressed"
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.state == "pressed"
            if self.rect.collidepoint(event.pos):
                self.state = "hovered"
                if was_pressed:
                    return True
            else:
                self.state = "default"
        return False

    def update_hover(self, mouse_pos):
        """À appeler chaque frame pour gérer le survol quand aucune touche n'est pressée."""
        if self.state != "pressed":
            self.state = "hovered" if self.rect.collidepoint(mouse_pos) else "default"

    def draw(self, screen):
        pieces = _get_button_pieces(self.state)
        bg = render_nine_slice(pieces, self.rect.width, self.rect.height, scale=config.UI_SCALE)
        screen.blit(bg, self.rect.topleft)

        label = self.font.render(self.text, True, (255, 255, 255))
        label_x = self.rect.centerx - label.get_width() // 2
        label_y = self.rect.centery - label.get_height() // 2
        screen.blit(label, (label_x, label_y))


class TextInput:
    def __init__(self, x, y, width, height, font, placeholder="", max_length=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.placeholder = placeholder
        self.text = ""
        self.max_length = max_length
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
        elif event.type == pygame.TEXTINPUT and self.active:
            if len(self.text) < self.max_length:
                self.text += event.text

    def draw(self, screen):
        border_color = (255, 255, 255) if self.active else (140, 140, 140)
        pygame.draw.rect(screen, (20, 20, 30), self.rect)
        pygame.draw.rect(screen, border_color, self.rect, width=2)

        display_text = self.text if self.text else self.placeholder
        text_color = (255, 255, 255) if self.text else (120, 120, 120)
        label = self.font.render(display_text, True, text_color)
        screen.blit(label, (self.rect.x + 6, self.rect.centery - label.get_height() // 2))