"""
CONFIG
"""

#tiles
TILE_SIZE = 16
SCALE = 4#tim c bon pour la taille ou pas??
DISPLAY_TILE_SIZE = TILE_SIZE * SCALE

#window
SCREEN_WIDTH = 1366
SCREEN_HEIGHT = 768
FPS = 60


def configure_screen_size(display_size):
    """Use the display resolution for the game surface."""
    global SCREEN_WIDTH, SCREEN_HEIGHT

    display_width, display_height = display_size
    SCREEN_WIDTH = display_width
    SCREEN_HEIGHT = display_height

#player
PLAYER_MAX_SPEED = 100
PLAYER_ACCEL = 450
PLAYER_FRICTION = 450

PLAYER_SIZE_MULTIPLIER = 0.75
PLAYER_HITBOX_WIDTH = 18*PLAYER_SIZE_MULTIPLIER
PLAYER_HITBOX_HEIGHT = 18*PLAYER_SIZE_MULTIPLIER

#sprite
PLAYER_SPRITE_WIDTH = 25
PLAYER_SPRITE_HEIGHT = 30
PLAYER_FOOT_ROW = 25

PLAYER_ANIMATION_FRAME_DURATION = {
    #spf
    "idle": 0.65,
    "walking": 0.12,
    "hurt": 0.08,
}

MAX_PLAYERS = 4

#settings
FONT_PATH = "assets/fonts/GrapeSoda.ttf"
FONT_SIZE_NORMAL = 20
FONT_SIZE_TITLE = 50
UI_SCALE = 4

GAME_TITLE = "Gembound"