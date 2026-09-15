import json
import os
import pygame

SETTINGS_PATH = "settings.json"

DEFAULT_RESOLUTIONS = [
    (1024, 576),
    (1152, 648),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
]

DEFAULT_KEYBINDS = {
    "up": [pygame.K_UP, pygame.K_z],
    "down": [pygame.K_DOWN, pygame.K_s],
    "left": [pygame.K_LEFT, pygame.K_q],
    "right": [pygame.K_RIGHT, pygame.K_d],
}


class Settings:
    def __init__(self):
        self.resolution = _detect_native_resolution()
        self.fullscreen = False
        self.keybinds = {k: list(v) for k, v in DEFAULT_KEYBINDS.items()}
        self.master_volume = 1.0#pas d'utilité mtn

    def to_dict(self):
        return {
            "resolution": list(self.resolution),
            "fullscreen": self.fullscreen,
            "keybinds": self.keybinds,
            "master_volume": self.master_volume,
        }

    @staticmethod
    def from_dict(data):
        settings = Settings()
        settings.resolution = tuple(data.get("resolution", settings.resolution))
        settings.fullscreen = data.get("fullscreen", False)
        settings.keybinds = data.get("keybinds", settings.keybinds)
        settings.master_volume = data.get("master_volume", 1.0)
        return settings


def _detect_native_resolution():
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return (info.current_w, info.current_h)
    except pygame.error:
        pass
    return DEFAULT_RESOLUTIONS[1]#repli


def load_settings():
    settings = Settings()

    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                data = json.load(f)
            settings = Settings.from_dict(data)
        except (json.JSONDecodeError, OSError):
            pass

    _clamp_to_native_resolution(settings)
    return settings


def _clamp_to_native_resolution(settings):
    native_w, native_h = _detect_native_resolution()
    saved_w, saved_h = settings.resolution
    if saved_w > native_w or saved_h > native_h:
        settings.resolution = (native_w, native_h)
        settings.fullscreen = False


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings.to_dict(), f, indent=2)
    except OSError:
        pass