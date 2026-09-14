import config

TILE_EMPTY = None

TILE_GROUND = "ground"

TILE_WALL_FRONT = "wall_front"
TILE_WALL_FRONT_L = "wall_front_l"
TILE_WALL_FRONT_R = "wall_front_r"
TILE_WALL_FRONT_M = "wall_front_m"

TILE_WALL_SIDE_L = "wall_side_l"
TILE_WALL_SIDE_R = "wall_side_r"

TILE_WALL_FRONT_CORNER_L = "wall_front_corner_l"
TILE_WALL_FRONT_CORNER_R = "wall_front_corner_r"

TILE_WALL_SOLID = "wall_solid"
TILE_WALL_SOLID_M = "wall_solid_m"
TILE_WALL_SOLID_L = "wall_solid_l"
TILE_WALL_SOLID_R = "wall_solid_r"

TILE_WALL_OVERLAY = "wall_overlay"
TILE_WALL_OVERLAY_BOTTOM = "wall_overlay_bottom"
TILE_KEY = "story_key"
TILE_DOOR = "story_door"

_FRONT_WALL_TYPES = {TILE_WALL_FRONT, TILE_WALL_FRONT_L, TILE_WALL_FRONT_R, TILE_WALL_FRONT_M}
_FRONT_HITBOX = (0, 0, 16, 9)
_FULL_HITBOX = (0, 0, 16, 16)


def _local_hitboxes(tile_type):
    if tile_type in (TILE_GROUND, TILE_KEY):
        return []
    if tile_type in _FRONT_WALL_TYPES:
        return [_FRONT_HITBOX]
    return [_FULL_HITBOX]


class DungeonRoom:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        self.overlay = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x, y):
        if not self.in_bounds(x, y):
            return TILE_EMPTY
        return self.tiles[y][x]

    def set(self, x, y, tile_type):
        if self.in_bounds(x, y):
            self.tiles[y][x] = tile_type

    def is_empty(self, x, y):
        return self.get(x, y) is TILE_EMPTY

    def set_overlay(self, x, y, tile_type):
        if self.in_bounds(x, y):
            self.overlay[y][x] = tile_type

    def is_walkable(self, x, y):
        return self.get(x, y) in (TILE_GROUND, TILE_KEY)

    def world_hitboxes(self, x, y):
        tile_type = self.get(x, y)
        result = []
        for (lx, ly, lw, lh) in _local_hitboxes(tile_type):
            result.append((
                x * config.TILE_SIZE + lx,
                y * config.TILE_SIZE + ly,
                lw,
                lh,
            ))
        return result

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "overlay": self.overlay,
        }

    @staticmethod
    def from_dict(data):
        room = DungeonRoom(data["width"], data["height"])
        room.tiles = data["tiles"]
        room.overlay = data["overlay"]
        return room


def find_walkable_near(room, x, y):
    if room.is_walkable(x, y):
        return x, y
    for radius in range(1, max(room.width, room.height)):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cx, cy = x + dx, y + dy
                if room.is_walkable(cx, cy):
                    return cx, cy
    return x, y


def get_spawn_positions(room, count):
    center_x = room.width // 2
    center_y = room.height // 2
    center_x, center_y = find_walkable_near(room, center_x, center_y)

    offsets = [(0, 0), (2, 0), (0, 2), (2, 2)]
    positions = []
    for i in range(count):
        dx, dy = offsets[i % len(offsets)]
        x, y = find_walkable_near(room, center_x + dx, center_y + dy)
        positions.append((x, y))
    return positions