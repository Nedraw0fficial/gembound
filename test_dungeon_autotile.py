from world.dungeon_autotile import autotile_room
from world.dungeon_tiles import (
    TILE_GROUND, TILE_WALL_FRONT, TILE_WALL_FRONT_L, TILE_WALL_FRONT_R, TILE_WALL_FRONT_M,
    TILE_WALL_SIDE_L, TILE_WALL_SIDE_R,
    TILE_WALL_FRONT_CORNER_L, TILE_WALL_FRONT_CORNER_R,
    TILE_WALL_SOLID, TILE_WALL_SOLID_M, TILE_WALL_SOLID_L, TILE_WALL_SOLID_R,
)

SYMBOLS = {
    None: ".",
    TILE_GROUND: "X",
    TILE_WALL_FRONT: "B",
    TILE_WALL_FRONT_L: "C",
    TILE_WALL_FRONT_R: "D",
    TILE_WALL_FRONT_M: "E",
    TILE_WALL_SIDE_L: "F",
    TILE_WALL_SIDE_R: "G",
    TILE_WALL_FRONT_CORNER_L: "H",
    TILE_WALL_FRONT_CORNER_R: "J",
    TILE_WALL_SOLID: "R",
    TILE_WALL_SOLID_M: "K",
    TILE_WALL_SOLID_L: "L",
    TILE_WALL_SOLID_R: "M",
}


def print_room(room):
    for y in range(room.height):
        row = []
        for x in range(room.width):
            tile = room.get(x, y)
            row.append(SYMBOLS.get(tile, "?"))
        print(" ".join(row))
    print()


ground_rect = [(x, y) for x in range(1, 7) for y in range(1, 5)]
room_rect = autotile_room(ground_rect, width=8, height=6)
print("=== Salle rectangulaire ===")
print_room(room_rect)

ground_l = [(x, y) for x in range(1, 7) for y in range(1, 3)]
ground_l += [(x, y) for x in range(4, 7) for y in range(3, 6)]
room_l = autotile_room(ground_l, width=8, height=7)
print("=== Salle en L ===")
print_room(room_l)