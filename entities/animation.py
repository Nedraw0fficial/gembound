import pygame
import config

ANIMATION_FILES = {
    "idle": "assets/sprites/player/bimbo_idle.png",
    "walking": "assets/sprites/player/bimbo_walking.png",
    "hurt": "assets/sprites/player/bimbo_hurt.png",
}

_raw_frames_cache = {}
_tinted_frames_cache = {}


def _load_raw_frames(animation_name):
    if animation_name in _raw_frames_cache:
        return _raw_frames_cache[animation_name]

    path = ANIMATION_FILES[animation_name]
    sheet = pygame.image.load(path).convert_alpha()
    frame_w = config.PLAYER_SPRITE_WIDTH
    frame_h = config.PLAYER_SPRITE_HEIGHT
    frame_count = sheet.get_width() // frame_w

    frames = []
    for i in range(frame_count):
        rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
        frames.append(sheet.subsurface(rect).copy())

    _raw_frames_cache[animation_name] = frames
    return frames


def _tint_frame(frame, color):
    tinted = frame.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def get_frames(animation_name, color, facing_left=False):
    cache_key = (animation_name, color, facing_left)
    if cache_key in _tinted_frames_cache:
        return _tinted_frames_cache[cache_key]

    raw_frames = _load_raw_frames(animation_name)
    result = []
    for frame in raw_frames:
        tinted = _tint_frame(frame, color)
        if facing_left:
            tinted = pygame.transform.flip(tinted, True, False)
        result.append(tinted)

    _tinted_frames_cache[cache_key] = result
    return result


class AnimationController:

    def __init__(self):
        self.current_animation = "idle"
        self.frame_index = 0
        self.time_in_frame = 0.0
        self.facing_left = False

    def set_animation(self, animation_name):
        if animation_name != self.current_animation:
            self.current_animation = animation_name
            self.frame_index = 0
            self.time_in_frame = 0.0

    def set_facing(self, facing_left):
        self.facing_left = facing_left

    def update(self, dt):
        duration = config.PLAYER_ANIMATION_FRAME_DURATION[self.current_animation]
        self.time_in_frame += dt
        if self.time_in_frame >= duration:
            self.time_in_frame -= duration
            frame_count = len(_load_raw_frames(self.current_animation))
            self.frame_index = (self.frame_index + 1) % frame_count

    def get_current_frame(self, color):
        frames = get_frames(self.current_animation, color, self.facing_left)
        return frames[self.frame_index % len(frames)]