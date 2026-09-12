import math


def generate_room_shape(rng, radius, blob_count=5):
    circles = []
    for _ in range(blob_count):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(0, radius * 0.5)
        cx = math.cos(angle) * dist
        cy = math.sin(angle) * dist
        r = rng.uniform(radius * 0.5, radius * 0.85)
        circles.append((cx, cy, r))

    margin = int(radius * 2.5)
    size = margin * 2

    floor_set = set()
    for gy in range(size):
        for gx in range(size):
            x = gx - margin
            y = gy - margin
            for cx, cy, r in circles:
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    floor_set.add((x, y))
                    break

    floor_set = _smooth(floor_set, passes=2)
    floor_set = _keep_largest_component(floor_set)
    floor_set = _limit_boundary_shift(floor_set)
    floor_set = _keep_largest_component(floor_set)

    return _normalize(floor_set)


def _smooth(floor_set, passes=2):
    current = set(floor_set)
    for _ in range(passes):
        candidates = set()
        for (x, y) in current:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    candidates.add((x + dx, y + dy))

        next_set = set()
        for (x, y) in candidates:
            neighbor_count = sum(
                1
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                if not (dx == 0 and dy == 0) and (x + dx, y + dy) in current
            )
            if neighbor_count >= 5:
                next_set.add((x, y))
        current = next_set
    return current


def _keep_largest_component(floor_set):
    remaining = set(floor_set)
    best_component = set()

    while remaining:
        start = next(iter(remaining))
        stack = [start]
        component = set()
        while stack:
            cell = stack.pop()
            if cell in component:
                continue
            component.add(cell)
            x, y = cell
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = (x + dx, y + dy)
                if neighbor in remaining and neighbor not in component:
                    stack.append(neighbor)
        remaining -= component
        if len(component) > len(best_component):
            best_component = component

    return best_component


def _limit_row_boundary_shift(floor_set):
    if not floor_set:
        return floor_set

    min_y = min(y for x, y in floor_set)
    max_y = max(y for x, y in floor_set)

    rows = {}
    for x, y in floor_set:
        rows.setdefault(y, set()).add(x)

    result = set()
    prev_min = None
    prev_max = None
    for y in range(min_y, max_y + 1):
        cols = rows.get(y)
        if not cols:
            prev_min = prev_max = None
            continue

        cur_min = min(cols)
        cur_max = max(cols)

        if prev_min is not None:
            cur_min = max(prev_min - 1, min(prev_min + 1, cur_min))
            cur_max = max(prev_max - 1, min(prev_max + 1, cur_max))
            if cur_max < cur_min:
                cur_max = cur_min

        for x in range(cur_min, cur_max + 1):
            result.add((x, y))
        prev_min, prev_max = cur_min, cur_max

    return result


def _limit_boundary_shift(floor_set):
    floor_set = _limit_row_boundary_shift(floor_set)
    transposed = {(y, x) for (x, y) in floor_set}
    transposed = _limit_row_boundary_shift(transposed)
    floor_set = {(y, x) for (x, y) in transposed}
    return floor_set


def _normalize(floor_set):
    if not floor_set:
        return []
    min_x = min(x for x, y in floor_set)
    min_y = min(y for x, y in floor_set)
    return [(x - min_x, y - min_y) for x, y in floor_set]