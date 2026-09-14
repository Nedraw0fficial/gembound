def generate_room_shape(rng, radius, feature_chance=0.85, max_features=4):
    actual_radius = radius * rng.uniform(0.55, 1.0)

    rect_count = rng.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]

    base_w = actual_radius * rng.uniform(1.3, 2.0)
    base_h = actual_radius * rng.uniform(1.0, 1.5)
    rects = [(-base_w / 2, -base_h / 2, base_w, base_h)]

    for _ in range(rect_count - 1):
        base_rect = rng.choice(rects)
        new_rect = _attach_rectangle(rng, base_rect, actual_radius)
        rects.append(new_rect)

    floor_set = set()
    for (rx, ry, rw, rh) in rects:
        for gx in range(int(round(rx)), int(round(rx + rw)) + 1):
            for gy in range(int(round(ry)), int(round(ry + rh)) + 1):
                floor_set.add((gx, gy))

    floor_set = _maybe_notch_corners(rng, floor_set)
    floor_set = _keep_largest_component(floor_set)
    floor_set = _add_interior_features(rng, floor_set, feature_chance, max_features)

    return _normalize(floor_set)


def _attach_rectangle(rng, base_rect, radius):
    bx, by, bw, bh = base_rect
    w = radius * rng.uniform(0.8, 1.4)
    h = radius * rng.uniform(0.8, 1.4)

    side = rng.choice(["left", "right", "top", "bottom"])

    if side in ("left", "right"):
        overlap_h = min(h, bh) * rng.uniform(0.5, 0.9)
        y = rng.uniform(by, by + bh - overlap_h) if bh > overlap_h else by
        y_center_offset = rng.uniform(-1, 1) * (bh * 0.1)
        y = max(by - h + overlap_h, min(by + bh - overlap_h, y)) + y_center_offset

        overlap_w = min(w, bw) * rng.uniform(0.15, 0.35)
        if side == "right":
            x = bx + bw - overlap_w
        else:
            x = bx - w + overlap_w
    else:
        overlap_w = min(w, bw) * rng.uniform(0.5, 0.9)
        x = rng.uniform(bx, bx + bw - overlap_w) if bw > overlap_w else bx
        x_center_offset = rng.uniform(-1, 1) * (bw * 0.1)
        x = max(bx - w + overlap_w, min(bx + bw - overlap_w, x)) + x_center_offset

        overlap_h = min(h, bh) * rng.uniform(0.15, 0.35)
        if side == "bottom":
            y = by + bh - overlap_h
        else:
            y = by - h + overlap_h

    return (x, y, w, h)


def _maybe_notch_corners(rng, floor_set):
    if not floor_set:
        return floor_set

    xs = [x for x, y in floor_set]
    ys = [y for x, y in floor_set]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    corners = [
        (min_x, min_y, 1, 1),
        (max_x, min_y, -1, 1),
        (min_x, max_y, 1, -1),
        (max_x, max_y, -1, -1),
    ]

    result = set(floor_set)
    for (cx, cy, dx, dy) in corners:
        if rng.random() > 0.35:
            continue
        notch_size = rng.randint(2, max(2, int((max_x - min_x) * 0.15)))
        cells_to_remove = set()
        for i in range(notch_size):
            for j in range(notch_size):
                cells_to_remove.add((cx + dx * i, cy + dy * j))

        candidate = result - cells_to_remove
        if len(_keep_largest_component(candidate)) >= len(candidate) * 0.9:
            result = candidate

    return result


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


def _feature_shapes(rng):
    shapes = []

    shapes.append([(0, 0)])
    shapes.append([(0, 0), (1, 0)])
    shapes.append([(0, 0), (0, 1)])
    shapes.append([(0, 0), (1, 0), (0, 1), (1, 1)])

    line_len = rng.randint(3, 5)
    shapes.append([(i, 0) for i in range(line_len)])
    shapes.append([(0, i) for i in range(line_len)])

    shapes.append([(0, 0), (1, 0), (0, 1)])
    shapes.append([(0, 0), (1, 0), (1, 1)])

    return shapes


def _add_interior_features(rng, floor_set, feature_chance, max_features, min_spacing=3):
    if rng.random() > feature_chance or max_features <= 0:
        return floor_set

    count = rng.randint(1, max_features)
    result = set(floor_set)

    xs = [x for x, y in floor_set]
    ys = [y for x, y in floor_set]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    placed_centers = []
    attempts = 0
    placed_count = 0
    while placed_count < count and attempts < 100:
        attempts += 1
        cx = rng.randint(min_x, max_x)
        cy = rng.randint(min_y, max_y)

        if any(abs(cx - px) < min_spacing and abs(cy - py) < min_spacing for px, py in placed_centers):
            continue

        shape = rng.choice(_feature_shapes(rng))
        if rng.random() < 0.5:
            shape = [(dy, dx) for dx, dy in shape]

        cells = [(cx + dx, cy + dy) for dx, dy in shape]

        if not all(c in result for c in cells):
            continue

        candidate = result - set(cells)
        if len(_keep_largest_component(candidate)) != len(candidate):
            continue

        result = candidate
        placed_centers.append((cx, cy))
        placed_count += 1

    return result


def _normalize(floor_set):
    if not floor_set:
        return []
    min_x = min(x for x, y in floor_set)
    min_y = min(y for x, y in floor_set)
    return [(x - min_x, y - min_y) for x, y in floor_set]

def generate_square_room(width, height):
    return [(x, y) for x in range(width) for y in range(height)]
