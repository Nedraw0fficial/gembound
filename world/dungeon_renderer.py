import pygame
import config
from world.dungeon_tiles import (
    TILE_GROUND,
    TILE_WALL_FRONT, TILE_WALL_FRONT_L, TILE_WALL_FRONT_R, TILE_WALL_FRONT_M,
    TILE_WALL_SIDE_L, TILE_WALL_SIDE_R,
    TILE_WALL_FRONT_CORNER_L, TILE_WALL_FRONT_CORNER_R,
    TILE_WALL_SOLID, TILE_WALL_SOLID_M, TILE_WALL_SOLID_L, TILE_WALL_SOLID_R,
    TILE_WALL_OVERLAY, TILE_WALL_OVERLAY_BOTTOM,
)

SPRITE_FILES = {
    TILE_GROUND: "dungeon_ground.png",
    TILE_WALL_FRONT: "dungeon_wall_front.png",
    TILE_WALL_FRONT_L: "dungeon_wall_front_l.png",
    TILE_WALL_FRONT_R: "dungeon_wall_front_r.png",
    TILE_WALL_FRONT_M: "dungeon_wall_front_m.png",
    TILE_WALL_SIDE_L: "dungeon_wall_side_l.png",
    TILE_WALL_SIDE_R: "dungeon_wall_side_r.png",
    TILE_WALL_FRONT_CORNER_L: "dungeon_wall_front_corner_l.png",
    TILE_WALL_FRONT_CORNER_R: "dungeon_wall_front_corner_r.png",
    TILE_WALL_SOLID: "dungeon_wall_solid.png",
    TILE_WALL_SOLID_M: "dungeon_wall_solid_m.png",
    TILE_WALL_SOLID_L: "dungeon_wall_solid_l.png",
    TILE_WALL_SOLID_R: "dungeon_wall_solid_r.png",
    TILE_WALL_OVERLAY: "dungeon_wall_overlay.png",
    TILE_WALL_OVERLAY_BOTTOM: "dungeon_wall_overlay_bottom.png",
}


class DungeonRenderer:
    def __init__(self):
        self.images = {}
        self._load_images()

    def _load_images(self):
        base_path = "assets/sprites/dungeon/"
        for tile_type, filename in SPRITE_FILES.items():
            img = pygame.image.load(base_path + filename).convert_alpha()
            img = pygame.transform.scale(
                img, (config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE)
            )
            self.images[tile_type] = img

    def render_main_layer(self, screen, room, camera_x, camera_y):
        dts = config.DISPLAY_TILE_SIZE
        first_col = max(0, camera_x // config.TILE_SIZE)
        first_row = max(0, camera_y // config.TILE_SIZE)
        visible_cols = config.SCREEN_WIDTH // dts + 2
        visible_rows = config.SCREEN_HEIGHT // dts + 2

        cam_offset_x = camera_x * config.SCALE
        cam_offset_y = camera_y * config.SCALE

        for row in range(first_row, min(room.height, first_row + visible_rows)):
            for col in range(first_col, min(room.width, first_col + visible_cols)):
                tile_type = room.get(col, row)
                if tile_type is None:
                    continue
                img = self.images.get(tile_type)
                if img is None:
                    continue
                screen_x = col * dts - cam_offset_x
                screen_y = row * dts - cam_offset_y
                screen.blit(img, (screen_x, screen_y))

    def render_overlay_layer(self, screen, room, camera_x, camera_y):
        dts = config.DISPLAY_TILE_SIZE
        first_col = max(0, camera_x // config.TILE_SIZE)
        first_row = max(0, camera_y // config.TILE_SIZE)
        visible_cols = config.SCREEN_WIDTH // dts + 2
        visible_rows = config.SCREEN_HEIGHT // dts + 2

        cam_offset_x = camera_x * config.SCALE
        cam_offset_y = camera_y * config.SCALE

        for row in range(first_row, min(room.height, first_row + visible_rows)):
            for col in range(first_col, min(room.width, first_col + visible_cols)):
                overlay_type = room.overlay[row][col]
                if overlay_type is None:
                    continue
                img = self.images.get(overlay_type)
                if img is None:
                    continue
                screen_x = col * dts - cam_offset_x
                screen_y = row * dts - cam_offset_y
                screen.blit(img, (screen_x, screen_y))