import pygame
import config
from world.tilemap import (
    GROUND_WATER, GROUND_SAND, GROUND_GRASS,
    TOP_NONE, TOP_TREE, TOP_ROCK,
    TOP_SPRITE_PIXEL_SIZE,
)

GROUND_SPRITE_FILES = {
    GROUND_WATER: "water.png",
    GROUND_SAND: "sand.png",
    GROUND_GRASS: "grass.png",
}

TOP_SPRITE_FILES = {
    TOP_TREE: "tree.png",
    TOP_ROCK: "rock.png",
}


class Renderer:
    def __init__(self):
        self.ground_images = {}
        self.top_images = {}
        self._load_images()

    def _load_images(self):
        base_path = "assets/sprites/tiles/"
        for tile_type, filename in GROUND_SPRITE_FILES.items():
            img = pygame.image.load(base_path + filename).convert()
            img = pygame.transform.scale(
                img, (config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE)
            )
            self.ground_images[tile_type] = img

        for tile_type, filename in TOP_SPRITE_FILES.items():
            img = pygame.image.load(base_path + filename).convert_alpha()
            pixel_size = TOP_SPRITE_PIXEL_SIZE[tile_type]
            display_size = pixel_size * config.SCALE
            img = pygame.transform.scale(img, (display_size, display_size))
            self.top_images[tile_type] = img

    def render(self, screen, tilemap, camera_x, camera_y):

        dts = config.DISPLAY_TILE_SIZE

        first_col = max(0, camera_x // config.TILE_SIZE)
        first_row = max(0, camera_y // config.TILE_SIZE)
        visible_cols = config.SCREEN_WIDTH // dts + 2
        visible_rows = config.SCREEN_HEIGHT // dts + 2

        cam_offset_x = camera_x * config.SCALE
        cam_offset_y = camera_y * config.SCALE

        #layer0
        for row in range(first_row, min(tilemap.height, first_row + visible_rows)):
            for col in range(first_col, min(tilemap.width, first_col + visible_cols)):
                ground_type = tilemap.get_ground(col, row)
                screen_x = col * dts - cam_offset_x
                screen_y = row * dts - cam_offset_y
                screen.blit(self.ground_images[ground_type], (screen_x, screen_y))

        #layer1 (above)
        for row in range(first_row, min(tilemap.height, first_row + visible_rows)):
            for col in range(first_col, min(tilemap.width, first_col + visible_cols)):
                top_type = tilemap.get_top(col, row)
                if top_type == TOP_NONE:
                    continue
                img = self.top_images[top_type]
                pixel_size = TOP_SPRITE_PIXEL_SIZE[top_type]
                display_size = pixel_size * config.SCALE
                center_offset = (display_size - dts) // 2

                screen_x = col * dts - cam_offset_x - center_offset
                screen_y = row * dts - cam_offset_y - center_offset
                screen.blit(img, (screen_x, screen_y))