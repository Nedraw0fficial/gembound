import pygame
import config
from entities.gate import CLOSING_FRAME_COUNT

BASE_PATH = "assets/sprites/dungeon/"


class GateRenderer:
    def __init__(self):
        self.open_images = {}
        self.locked_images = {}
        self._load_images()

    def _load_images(self):
        for orientation in ("f", "l", "r"):
            path = f"{BASE_PATH}gate_open_{orientation}.png"
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE))
            self.open_images[orientation] = img

            for frame in range(CLOSING_FRAME_COUNT):
                path = f"{BASE_PATH}gate_locked_{orientation}_{frame}.png"
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE))
                self.locked_images[(orientation, frame)] = img

    def render(self, screen, gates, camera_x, camera_y):
        cam_offset_x = camera_x * config.SCALE
        cam_offset_y = camera_y * config.SCALE
        dts = config.DISPLAY_TILE_SIZE

        for gate in gates:
            kind, orientation, frame_index = gate.sprite_key()
            if kind == "open":
                img = self.open_images[orientation]
            else:
                img = self.locked_images[(orientation, frame_index)]

            for (x, y) in gate.tiles:
                screen_x = x * dts - cam_offset_x
                screen_y = y * dts - cam_offset_y
                screen.blit(img, (screen_x, screen_y))

