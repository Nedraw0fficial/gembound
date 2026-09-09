import random
import math
from world.tilemap import (
    Tilemap,
    GROUND_WATER, GROUND_SAND, GROUND_GRASS,
    TOP_NONE, TOP_TREE, TOP_ROCK,
)

WATER_THRESHOLD = 0.44
SAND_MARGIN = 0.05

LAKE_THRESHOLD = 0.80
LAKE_MIN_LAND_VALUE = 0.62

TREE_CHANCE_MIN = 0.02
TREE_CHANCE_MAX = 0.20
ROCK_CHANCE = 0.025

SPAWN_CLEAR_RADIUS = 3
SPAWN_OFFSETS = [(0, 0), (2, 0), (0, 2), (2, 2)]



def _generate_grid_points(width, height, cell_size, rng):
    cols = width // cell_size + 2
    rows = height // cell_size + 2
    return [[rng.uniform(0, 1) for _ in range(cols)] for _ in range(rows)]


def _smooth_step(t):
    return t * t * (3 - 2 * t)


def _sample_noise(grid, x, y, cell_size):
    gx = x / cell_size
    gy = y / cell_size
    col = int(gx)
    row = int(gy)
    fx = _smooth_step(gx - col)
    fy = _smooth_step(gy - row)

    top_left = grid[row][col]
    top_right = grid[row][col + 1]
    bottom_left = grid[row + 1][col]
    bottom_right = grid[row + 1][col + 1]

    top = top_left + (top_right - top_left) * fx
    bottom = bottom_left + (bottom_right - bottom_left) * fx
    return top + (bottom - top) * fy


def generate_island(width, height, seed=None):
    rng = random.Random(seed)
    tilemap = Tilemap(width, height)

    center_x, center_y = width / 2, height / 2
    max_dist = math.hypot(center_x, center_y)

    shape_grid = _generate_grid_points(width, height, 25, rng)
    coast_grid = _generate_grid_points(width, height, 8, rng)
    lake_grid = _generate_grid_points(width, height, 14, rng)
    forest_density_grid = _generate_grid_points(width, height, 20, rng)

    land_values = [[0.0] * width for _ in range(height)]

    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - center_x, y - center_y) / max_dist
            shape_noise = _sample_noise(shape_grid, x, y, 25) * 0.3
            coast_noise = _sample_noise(coast_grid, x, y, 8) * 0.15

            land_value = (1 - dist) + shape_noise + coast_noise - 0.15
            land_values[y][x] = land_value

            if land_value < WATER_THRESHOLD:
                tilemap.set_ground(x, y, GROUND_WATER)
            elif land_value < WATER_THRESHOLD + SAND_MARGIN:
                tilemap.set_ground(x, y, GROUND_SAND)
            else:
                tilemap.set_ground(x, y, GROUND_GRASS)

    for y in range(height):
        for x in range(width):
            if tilemap.get_ground(x, y) != GROUND_GRASS:
                continue
            if land_values[y][x] < LAKE_MIN_LAND_VALUE:
                continue
            lake_noise = _sample_noise(lake_grid, x, y, 14)
            if lake_noise > LAKE_THRESHOLD:
                tilemap.set_ground(x, y, GROUND_WATER)

    for y in range(height):
        for x in range(width):
            if tilemap.get_ground(x, y) != GROUND_GRASS:
                continue

            density_noise = _sample_noise(forest_density_grid, x, y, 20)
            tree_chance = TREE_CHANCE_MIN + density_noise * (TREE_CHANCE_MAX - TREE_CHANCE_MIN)

            roll = rng.random()
            if roll < ROCK_CHANCE:
                tilemap.set_top(x, y, TOP_ROCK)
            elif roll < ROCK_CHANCE + tree_chance:
                tilemap.set_top(x, y, TOP_TREE)

    return tilemap


def find_spawn_point(tilemap):
    center_x, center_y = tilemap.width // 2, tilemap.height // 2

    spawn_x, spawn_y = center_x, center_y   #fallback
    for radius in range(0, max(tilemap.width, tilemap.height) // 2):
        found = False
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x, y = center_x + dx, center_y + dy
                if not tilemap.in_bounds(x, y):
                    continue
                if tilemap.get_ground(x, y) == GROUND_GRASS and tilemap.is_walkable(x, y):
                    spawn_x, spawn_y = x, y
                    found = True
                    break
            if found:
                break
        if found:
            break

    clear_spawn_area(tilemap, spawn_x, spawn_y)
    return spawn_x, spawn_y

def clear_spawn_area(tilemap, center_x, center_y, radius=SPAWN_CLEAR_RADIUS):
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = center_x + dx, center_y + dy
            if not tilemap.in_bounds(x, y):
                continue
            if tilemap.get_ground(x, y) == GROUND_WATER:
                tilemap.set_ground(x, y, GROUND_GRASS)
            tilemap.set_top(x, y, TOP_NONE)

def spawn_position_for_slot(center_x, center_y, slot_index):
    """slot_index : 0 à 3, correspond à un des 4 emplacements fixes garantis libres."""
    dx, dy = SPAWN_OFFSETS[slot_index % len(SPAWN_OFFSETS)]
    return center_x + dx, center_y + dy