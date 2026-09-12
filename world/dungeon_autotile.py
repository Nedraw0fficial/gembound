from world.dungeon_tiles import (
    DungeonRoom,
    TILE_GROUND,
    TILE_WALL_FRONT, TILE_WALL_FRONT_L, TILE_WALL_FRONT_R, TILE_WALL_FRONT_M,
    TILE_WALL_SIDE_L, TILE_WALL_SIDE_R,
    TILE_WALL_FRONT_CORNER_L, TILE_WALL_FRONT_CORNER_R,
    TILE_WALL_SOLID, TILE_WALL_SOLID_M, TILE_WALL_SOLID_L, TILE_WALL_SOLID_R,
    TILE_WALL_OVERLAY, TILE_WALL_OVERLAY_BOTTOM,
)


def _is_ground(room, x, y):
    return room.get(x, y) == TILE_GROUND


def _pass_place_front_m_above_ground(room):
    for y in range(room.height):
        for x in range(room.width):
            if _is_ground(room, x, y) and room.is_empty(x, y - 1):
                room.set(x, y - 1, TILE_WALL_FRONT_M)


def _pass_resolve_front_variants(room):
    for y in range(room.height):
        for x in range(room.width):
            if room.get(x, y) != TILE_WALL_FRONT_M:
                continue
            ground_left = _is_ground(room, x - 1, y)
            ground_right = _is_ground(room, x + 1, y)

            if not ground_left and not ground_right:
                room.set(x, y, TILE_WALL_FRONT)
            elif ground_left and not ground_right:
                room.set(x, y, TILE_WALL_FRONT_L)
            elif ground_right and not ground_left:
                room.set(x, y, TILE_WALL_FRONT_R)


def _pass_place_side_walls(room):
    for y in range(room.height):
        ground_columns = [x for x in range(room.width) if _is_ground(room, x, y)]
        if not ground_columns:
            continue
        leftmost = min(ground_columns)
        rightmost = max(ground_columns)
        if room.is_empty(leftmost - 1, y):
            room.set(leftmost - 1, y, TILE_WALL_SIDE_L)
        if room.is_empty(rightmost + 1, y):
            room.set(rightmost + 1, y, TILE_WALL_SIDE_R)


def _pass_place_solid_below_ground(room):
    for y in range(room.height):
        for x in range(room.width):
            if _is_ground(room, x, y) and room.is_empty(x, y + 1):
                room.set(x, y + 1, TILE_WALL_SOLID)


def _pass_place_front_corners(room):
    for y in range(room.height):
        for x in range(room.width):
            tile = room.get(x, y)
            if tile == TILE_WALL_SIDE_L and room.is_empty(x, y - 1):
                room.set(x, y - 1, TILE_WALL_FRONT_CORNER_L)
            elif tile == TILE_WALL_SIDE_R and room.is_empty(x, y - 1):
                room.set(x, y - 1, TILE_WALL_FRONT_CORNER_R)


def _pass_place_solid_below_side_walls(room):
    for y in range(room.height):
        for x in range(room.width):
            tile = room.get(x, y)
            if tile in (TILE_WALL_SIDE_L, TILE_WALL_SIDE_R) and room.is_empty(x, y + 1):
                room.set(x, y + 1, TILE_WALL_SOLID)


def _pass_fill_remaining_solid(room):
    any_change = False
    for y in range(room.height - 1, -1, -1):
        row_before = [room.is_empty(x, y) for x in range(room.width)]

        def was_filled(x):
            if 0 <= x < room.width:
                return not row_before[x]
            return False

        decisions = []
        for x in range(room.width):
            if not row_before[x]:
                continue

            left_filled = was_filled(x - 1)
            right_filled = was_filled(x + 1)
            below_filled = not room.is_empty(x, y + 1)

            if left_filled and right_filled and below_filled:
                decisions.append((x, TILE_WALL_SOLID_M))
            elif right_filled and below_filled:
                decisions.append((x, TILE_WALL_SOLID_R))
            elif left_filled and below_filled:
                decisions.append((x, TILE_WALL_SOLID_L))
            elif left_filled and right_filled:
                decisions.append((x, TILE_WALL_SOLID))

        for x, tile_type in decisions:
            room.set(x, y, tile_type)

        any_change = any_change or bool(decisions)

    return any_change


def _pass_solid_above_everything(room):
    decisions = []
    for y in range(room.height):
        for x in range(room.width):
            if not room.is_empty(x, y) and room.is_empty(x, y - 1):
                decisions.append((x, y - 1))
    for x, y in decisions:
        room.set(x, y, TILE_WALL_SOLID)


def _pass_overlay_on_ground_edges(room):
    for y in range(room.height):
        for x in range(room.width):
            if _is_ground(room, x, y) and not _is_ground(room, x, y + 1):
                room.set_overlay(x, y, TILE_WALL_OVERLAY)

def _pass_overlay_bottom_below_overlay(room):
    positions = []
    for y in range(room.height):
        for x in range(room.width):
            if room.overlay[y][x] == TILE_WALL_OVERLAY:
                positions.append((x, y + 1))
    for x, y in positions:
        room.set_overlay(x, y, TILE_WALL_OVERLAY_BOTTOM)


def autotile_room(ground_positions, width, height):
    room = DungeonRoom(width, height)
    for x, y in ground_positions:
        room.set(x, y, TILE_GROUND)

    _pass_place_front_m_above_ground(room)
    _pass_resolve_front_variants(room)
    _pass_place_side_walls(room)
    _pass_place_solid_below_ground(room)
    _pass_place_front_corners(room)
    _pass_place_solid_below_side_walls(room)

    for _ in range(5):
        if not _pass_fill_remaining_solid(room):
            break

    _pass_solid_above_everything(room)
    _pass_overlay_on_ground_edges(room)
    _pass_overlay_bottom_below_overlay(room)

    return room