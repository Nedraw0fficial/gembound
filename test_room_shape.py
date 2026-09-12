import random
from world.room_shape import generate_room_shape
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


for seed in [1, 2, 3]:
    rng = random.Random(seed)
    shape = generate_room_shape(rng, radius=6, blob_count=5)

    max_x = max(x for x, y in shape)
    max_y = max(y for x, y in shape)
    ground_positions = [(x + 2, y + 2) for x, y in shape]

    room = autotile_room(ground_positions, width=max_x + 5, height=max_y + 5)
    print(f"=== Seed {seed} ===")
    print_room(room)