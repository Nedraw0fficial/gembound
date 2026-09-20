import pygame
import config

BASE_PATH = "assets/sprites/ui/"


class HealthBarRenderer:
    def __init__(self):
        self.own_bg = pygame.image.load(BASE_PATH + "health_bar.png").convert_alpha()
        self.own_slice = pygame.image.load(BASE_PATH + "health_slice.png").convert_alpha()

        self.other_bg = pygame.image.load(BASE_PATH + "health_bar_o.png").convert_alpha()
        self.other_slice = pygame.image.load(BASE_PATH + "health_slice_o.png").convert_alpha()

    def _build_fill_surface(self, slice_img, fill_width, fill_height, filled, white, color):
        surface = pygame.Surface((fill_width, fill_height), pygame.SRCALPHA)

        filled = max(0, min(fill_width, int(round(filled))))
        white = max(0, min(fill_width - filled, int(round(white))))

        tinted_slice = slice_img.copy()
        tinted_slice.fill(color, special_flags=pygame.BLEND_RGBA_MULT)

        white_slice = slice_img.copy()
        white_slice.fill(config.HEALTH_FLASH_COLOR, special_flags=pygame.BLEND_RGBA_MULT)

        for i in range(filled):
            surface.blit(tinted_slice, (i, 0))
        for i in range(white):
            surface.blit(white_slice, (filled + i, 0))

        return surface

    def render_own(self, screen, health_display, real_hp, color=None):
        color = color or config.HEALTH_COLOR_NORMAL
        filled, white = health_display.get_segments(real_hp)

        fill = self._build_fill_surface(
            self.own_slice,
            config.HEALTH_BAR_OWN_FILL_WIDTH, config.HEALTH_BAR_OWN_FILL_HEIGHT,
            filled, white, color,
        )

        scale = config.HEALTH_BAR_SCALE
        bg_scaled = pygame.transform.scale(
            self.own_bg, (self.own_bg.get_width() * scale, self.own_bg.get_height() * scale)
        )
        fill_scaled = pygame.transform.scale(
            fill, (fill.get_width() * scale, fill.get_height() * scale)
        )

        bar_x = config.SCREEN_WIDTH // 2 - bg_scaled.get_width() // 2
        bar_y = config.SCREEN_HEIGHT - bg_scaled.get_height() - 16

        screen.blit(bg_scaled, (bar_x, bar_y))
        screen.blit(fill_scaled, (
            bar_x + config.HEALTH_BAR_OWN_PADDING_X * scale,
            bar_y + config.HEALTH_BAR_OWN_PADDING_Y * scale,
        ))

    def render_other(self, screen, health_display, real_hp, screen_x, screen_y, color=None):
        color = color or config.HEALTH_COLOR_NORMAL
        filled, white = health_display.get_segments(real_hp)

        fill = self._build_fill_surface(
            self.other_slice,
            config.HEALTH_BAR_OTHER_FILL_WIDTH, config.HEALTH_BAR_OTHER_FILL_HEIGHT,
            filled, white, color,
        )

        scale = config.HEALTH_BAR_SCALE
        bg_scaled = pygame.transform.scale(
            self.other_bg, (self.other_bg.get_width() * scale, self.other_bg.get_height() * scale)
        )
        fill_scaled = pygame.transform.scale(
            fill, (fill.get_width() * scale, fill.get_height() * scale)
        )

        bg_x = screen_x - bg_scaled.get_width() // 2
        screen.blit(bg_scaled, (bg_x, screen_y))
        screen.blit(fill_scaled, (bg_x, screen_y))