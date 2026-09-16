PLAZA_SIZE = 5
GATE_SAFE_MARGIN = 3

def generate_corridor_positions(rng, layout):
    corridor_cells = set()
    seen_pairs = set()

    for node in layout.all_nodes():
        for direction, neighbor in node.connections.items():
            pair_key = frozenset((node.id, neighbor.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            opposite = {"north": "south", "south": "north", "east": "west", "west": "east"}[direction]
            start_x, start_y, width = node.doors[direction]
            end_x, end_y, _ = neighbor.doors[opposite]

            corridor_cells |= _trace_l_corridor((start_x, start_y), (end_x, end_y), width)

    return corridor_cells


def _too_close_to_door(cell, door_point, margin=GATE_SAFE_MARGIN):
    return max(abs(cell[0] - door_point[0]), abs(cell[1] - door_point[1])) <= margin


def _trace_l_corridor(start, end, width):
    sx, sy = start
    ex, ey = end
    cells = set()
    half = width // 2

    x_lo, x_hi = min(sx, ex), max(sx, ex)
    for x in range(x_lo, x_hi + 1):
        for w in range(-half, width - half):
            cells.add((x, sy + w))

    y_lo, y_hi = min(sy, ey), max(sy, ey)
    for y in range(y_lo, y_hi + 1):
        for w in range(-half, width - half):
            cells.add((ex + w, y))

    if sx != ex and sy != ey:
        plaza_half = PLAZA_SIZE // 2
        for dx in range(-plaza_half, PLAZA_SIZE - plaza_half):
            for dy in range(-plaza_half, PLAZA_SIZE - plaza_half):
                cell = (ex + dx, sy + dy)
                # jamais de carrefour élargi trop près d'une porte de salle (gates)
                if _too_close_to_door(cell, start) or _too_close_to_door(cell, end):
                    continue
                cells.add(cell)

    return cells