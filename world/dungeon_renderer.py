import pygame
import config
from entities.animation import AnimationController
from world.dungeon_tiles import (
    TILE_GROUND,
    TILE_KEY, TILE_DOOR,
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
        self.npc_animations = {}
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
                img = self.images.get(tile_type, self.images[TILE_GROUND])
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

    def render_story_layer(self, screen, room, camera_x, camera_y, story, dt=0.0, player_position=None):
        if not story or not story.get("enabled"):
            return

        dts = config.DISPLAY_TILE_SIZE

        for landmark in story.get("landmarks", []):
            landmark_x, landmark_y = landmark["position"]
            screen_x = landmark_x * dts - camera_x * config.SCALE
            screen_y = landmark_y * dts - camera_y * config.SCALE
            center = (screen_x + dts // 2, screen_y + dts // 2)
            if landmark["type"] == "lore_stone":
                pygame.draw.rect(screen, (95, 105, 120), (screen_x + 16, screen_y + 12, dts - 32, dts - 18))
                pygame.draw.line(screen, (190, 210, 225), (screen_x + 25, screen_y + 25), (screen_x + dts - 25, screen_y + 25), 3)
                pygame.draw.line(screen, (190, 210, 225), (screen_x + 25, screen_y + 35), (screen_x + dts - 30, screen_y + 35), 3)
            elif landmark["type"] == "passage_rune":
                pygame.draw.circle(screen, (65, 190, 205), center, 22, 4)
                pygame.draw.circle(screen, (170, 245, 235), center, 8, 3)
            else:
                pygame.draw.rect(screen, (120, 75, 38), (screen_x + 10, screen_y + 22, dts - 20, dts - 25))
                pygame.draw.line(screen, (240, 190, 70), (screen_x + 15, screen_y + 28), (screen_x + dts - 15, screen_y + 28), 3)

        for npc in story.get("npcs", []):
            npc_x = npc.get("x", npc["position"][0] * config.TILE_SIZE)
            npc_y = npc.get("y", npc["position"][1] * config.TILE_SIZE)
            screen_x = npc_x * config.SCALE - camera_x * config.SCALE
            screen_y = npc_y * config.SCALE - camera_y * config.SCALE
            animation = self.npc_animations.setdefault(npc["id"], AnimationController())
            animation.set_animation("walking" if abs(npc.get("vx", 0)) + abs(npc.get("vy", 0)) > 0 else "idle")
            animation.set_facing(npc.get("facing_left", False))
            animation.update(dt)
            frame = animation.get_current_frame(tuple(npc["costume"]["color"]))
            sprite_w = int(config.PLAYER_SPRITE_WIDTH * config.SCALE * config.PLAYER_SIZE_MULTIPLIER)
            sprite_h = int(config.PLAYER_SPRITE_HEIGHT * config.SCALE * config.PLAYER_SIZE_MULTIPLIER)
            sprite_x = screen_x + (dts - sprite_w) // 2
            sprite_y = screen_y + dts - config.PLAYER_FOOT_ROW * config.SCALE
            screen.blit(pygame.transform.scale(frame, (sprite_w, sprite_h)), (sprite_x, sprite_y))

            center_x = sprite_x + sprite_w // 2
            head_y = sprite_y + 12
            costume = npc["costume"]["style"]
            if costume == "cape":
                pygame.draw.polygon(screen, (45, 35, 110), [(sprite_x + 4, sprite_y + 28), (sprite_x + sprite_w - 4, sprite_y + 28), (sprite_x + sprite_w + 5, sprite_y + sprite_h), (sprite_x - 5, sprite_y + sprite_h)])
            elif costume == "hat":
                pygame.draw.polygon(screen, (55, 35, 25), [(center_x - 22, head_y + 10), (center_x, head_y - 8), (center_x + 22, head_y + 10)])
            elif costume == "helmet":
                pygame.draw.rect(screen, (175, 175, 185), (center_x - 18, head_y - 7, 36, 20))
            elif costume == "hood":
                pygame.draw.arc(screen, (35, 95, 75), (center_x - 24, head_y - 14, 48, 42), 0, 3.14, 7)
            elif costume == "crown":
                pygame.draw.polygon(screen, (245, 210, 65), [(center_x - 18, head_y + 3), (center_x - 12, head_y - 9), (center_x, head_y + 1), (center_x + 12, head_y - 9), (center_x + 18, head_y + 3)])
            elif costume == "mask":
                pygame.draw.rect(screen, (55, 35, 45), (center_x - 15, head_y + 4, 30, 10))
            if npc["id"] in story.get("talked_npcs", []):
                pygame.draw.circle(screen, (100, 220, 130), (sprite_x + sprite_w + 8, sprite_y + 4), 4)

            if player_position and not story.get("dialogue") and npc["id"] not in story.get("talked_npcs", []):
                distance = ((player_position["x"] - npc_x) ** 2 + (player_position["y"] - npc_y) ** 2) ** 0.5
                if distance <= config.TILE_SIZE * 1.5:
                    prompt = pygame.font.Font(config.FONT_PATH, 18).render("E : parler", True, (255, 240, 150))
                    screen.blit(prompt, (sprite_x - prompt.get_width() // 2 + sprite_w // 2, sprite_y - 26))

        key_position = story.get("key_position")
        if key_position and not story.get("key_collected"):
            key_x, key_y = key_position
            center = (
                key_x * dts - camera_x * config.SCALE + dts // 2,
                key_y * dts - camera_y * config.SCALE + dts // 2,
            )
            pygame.draw.circle(screen, (245, 210, 65), center, 12)
            pygame.draw.rect(screen, (245, 210, 65), (center[0], center[1] - 3, 22, 6))

        door_position = story.get("door_position")
        if door_position:
            door_x, door_y = door_position
            screen_x = door_x * dts - camera_x * config.SCALE
            screen_y = door_y * dts - camera_y * config.SCALE
            if story.get("door_unlocked"):
                pygame.draw.rect(screen, (45, 30, 25), (screen_x + 8, screen_y, dts - 16, dts))
                pygame.draw.rect(screen, (180, 145, 65), (screen_x + 8, screen_y, dts - 16, 5))
            else:
                pygame.draw.rect(screen, (100, 55, 35), (screen_x + 8, screen_y, dts - 16, dts))
                pygame.draw.circle(screen, (245, 210, 65), (screen_x + dts - 18, screen_y + dts // 2), 3)