import math
import config

HITBOX_SIZE = 12
HITBOX_OFFSET = (config.TILE_SIZE - HITBOX_SIZE) / 2


def new_player_state(x, y):
    return {"x": float(x), "y": float(y), "vx": 0.0, "vy": 0.0}


def _get_direction(keys):
    dx, dy = 0.0, 0.0
    if keys.get("up"):
        dy -= 1.0
    if keys.get("down"):
        dy += 1.0
    if keys.get("left"):
        dx -= 1.0
    if keys.get("right"):
        dx += 1.0

    length = math.hypot(dx, dy)
    if length > 0: #normalise
        dx /= length
        dy /= length
    return dx, dy


def _hitbox_corners(x, y):
    left = x + HITBOX_OFFSET
    top = y + HITBOX_OFFSET
    return [
        (left, top),
        (left + HITBOX_SIZE, top),
        (left, top + HITBOX_SIZE),
        (left + HITBOX_SIZE, top + HITBOX_SIZE),
    ]


def _can_move_to(x, y, tilemap):
    for px, py in _hitbox_corners(x, y):
        tile_x = int(px) // config.TILE_SIZE
        tile_y = int(py) // config.TILE_SIZE
        if not tilemap.is_walkable(tile_x, tile_y):
            return False
    return True


def update_player(state, keys, dt, tilemap):
    dir_x, dir_y = _get_direction(keys)

    if dir_x != 0 or dir_y != 0:
        state["vx"] += dir_x * config.PLAYER_ACCEL * dt
        state["vy"] += dir_y * config.PLAYER_ACCEL * dt
    else:
        speed = math.hypot(state["vx"], state["vy"])
        if speed > 0:
            new_speed = max(0.0, speed - config.PLAYER_FRICTION * dt)
            factor = new_speed / speed
            state["vx"] *= factor
            state["vy"] *= factor

    speed = math.hypot(state["vx"], state["vy"])
    if speed > config.PLAYER_MAX_SPEED:
        factor = config.PLAYER_MAX_SPEED / speed
        state["vx"] *= factor
        state["vy"] *= factor

    new_x = state["x"] + state["vx"] * dt
    if _can_move_to(new_x, state["y"], tilemap):
        state["x"] = new_x
    else:
        state["vx"] = 0.0

    new_y = state["y"] + state["vy"] * dt
    if _can_move_to(state["x"], new_y, tilemap):
        state["y"] = new_y
    else:
        state["vy"] = 0.0