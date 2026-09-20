import math
import config

HITBOX_WIDTH = config.PLAYER_HITBOX_WIDTH
HITBOX_HEIGHT = config.PLAYER_HITBOX_HEIGHT
HITBOX_OFFSET_X = (config.TILE_SIZE - HITBOX_WIDTH) / 2
HITBOX_OFFSET_Y = (config.TILE_SIZE - HITBOX_HEIGHT) / 2 - 4


def new_player_state(x, y):
    return {
        "x": float(x), "y": float(y), "vx": 0.0, "vy": 0.0,
        "hp": float(config.PLAYER_MAX_HP), "max_hp": float(config.PLAYER_MAX_HP),
    }


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
    if length > 0:
        dx /= length
        dy /= length
    return dx, dy


def _rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _can_move_to(x, y, room, gates):
    player_rect = (x + HITBOX_OFFSET_X, y + HITBOX_OFFSET_Y, HITBOX_WIDTH, HITBOX_HEIGHT)

    tile_x0 = int((x + HITBOX_OFFSET_X) // config.TILE_SIZE)
    tile_x1 = int((x + HITBOX_OFFSET_X + HITBOX_WIDTH) // config.TILE_SIZE)
    tile_y0 = int((y + HITBOX_OFFSET_Y) // config.TILE_SIZE)
    tile_y1 = int((y + HITBOX_OFFSET_Y + HITBOX_HEIGHT) // config.TILE_SIZE)

    for ty in range(tile_y0, tile_y1 + 1):
        for tx in range(tile_x0, tile_x1 + 1):
            for rect in room.world_hitboxes(tx, ty):
                if _rects_overlap(player_rect, rect):
                    return False

    for gate in gates:
        for rect in gate.world_hitboxes():
            if _rects_overlap(player_rect, rect):
                return False

    return True


def update_player(state, keys, dt, room, gates=()):
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
    if _can_move_to(new_x, state["y"], room, gates):
        state["x"] = new_x
    else:
        state["vx"] = 0.0

    new_y = state["y"] + state["vy"] * dt
    if _can_move_to(state["x"], new_y, room, gates):
        state["y"] = new_y
    else:
        state["vy"] = 0.0
