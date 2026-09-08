GROUND_WATER = "water"
GROUND_SAND = "sand"
GROUND_GRASS = "grass"

TOP_NONE = "none"
TOP_TREE = "tree"
TOP_ROCK = "rock"


class Tilemap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground = [[GROUND_WATER for _ in range(width)] for _ in range(height)]
        self.top = [[TOP_NONE for _ in range(width)] for _ in range(height)]

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_ground(self, x, y):
        return self.ground[y][x]

    def set_ground(self, x, y, tile_type):
        self.ground[y][x] = tile_type

    def get_top(self, x, y):
        return self.top[y][x]

    def set_top(self, x, y, tile_type):
        self.top[y][x] = tile_type

    def remove_top(self, x, y):
        """Miner/Casser"""
        self.top[y][x] = TOP_NONE

    def is_walkable(self, x, y):
        if not self.in_bounds(x, y):
            return False
        if self.ground[y][x] == GROUND_WATER:
            return False
        if self.top[y][x] in (TOP_TREE, TOP_ROCK):
            return False
        return True

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "ground": self.ground,
            "top": self.top,
        }

    @staticmethod
    def from_dict(data):
        tilemap = Tilemap(data["width"], data["height"])
        tilemap.ground = data["ground"]
        tilemap.top = data["top"]
        return tilemap


TOP_SPRITE_PIXEL_SIZE = {
    TOP_NONE: 16,
    TOP_TREE: 28,
    TOP_ROCK: 22,
}