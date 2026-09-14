# world/dungeon_layout.py — disposition du donjon : placement en coordonnées réelles

import random
from world.room_shape import generate_room_shape, generate_square_room

ROOM_TYPE_START = "start"
ROOM_TYPE_END = "end"
ROOM_TYPE_FIGHT = "fight"
ROOM_TYPE_NORMAL = "normal"

DIRECTIONS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

MAX_ROOM_WIDTH = 22
MAX_ROOM_HEIGHT = 16

CORRIDOR_MIN_LENGTH = 5
CORRIDOR_MAX_LENGTH = 16
CORRIDOR_MIN_WIDTH = 2
CORRIDOR_MAX_WIDTH = 3

PLACEMENT_BUFFER = 2


class RoomNode:
    def __init__(self, node_id, room_type=ROOM_TYPE_NORMAL):
        self.id = node_id
        self.room_type = room_type

        self.shape = None
        self.world_offset = None
        self.bounds = None

        self.connections = {}
        self.connection_widths = {}
        self.doors = {}

        self.is_cleared = False
        self.doors_open = True

    def shape_width(self):
        return max(x for x, y in self.shape) + 1

    def shape_height(self):
        return max(y for x, y in self.shape) + 1


class DungeonLayout:
    def __init__(self):
        self.nodes = []
        self.start_node = None
        self.end_node = None

    def all_nodes(self):
        return self.nodes


def _generate_capped_shape(rng, room_radius, feature_chance, max_features):
    radius = room_radius
    for _ in range(6):
        shape = generate_room_shape(rng, radius, feature_chance, max_features)
        w = max(x for x, y in shape) + 1
        h = max(y for x, y in shape) + 1
        if w <= MAX_ROOM_WIDTH and h <= MAX_ROOM_HEIGHT:
            return shape
        radius *= 0.8
    return shape


def _bounds_overlap(a, b, buffer=PLACEMENT_BUFFER):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + buffer < bx0 or bx1 + buffer < ax0 or
        ay1 + buffer < by0 or by1 + buffer < ay0
    )


def _door_anchor_local(shape, direction):
    if direction == "north":
        edge_y = min(y for x, y in shape)
        candidates = sorted(x for x, y in shape if y == edge_y)
    elif direction == "south":
        edge_y = max(y for x, y in shape)
        candidates = sorted(x for x, y in shape if y == edge_y)
    elif direction == "west":
        edge_x = min(x for x, y in shape)
        candidates = sorted(y for x, y in shape if x == edge_x)
    else:
        edge_x = max(x for x, y in shape)
        candidates = sorted(y for x, y in shape if x == edge_x)

    mid = candidates[len(candidates) // 2]
    if direction in ("north", "south"):
        return (mid, edge_y)
    return (edge_x, mid)


def generate_dungeon_layout(rng, room_count=6, room_radius=8, feature_chance=0.85,
                             max_features=4, extra_connection_chance=0.2):
    layout = DungeonLayout()

    start_node = RoomNode(0, room_type=ROOM_TYPE_START)
    start_node.shape = generate_square_room(10, 10)
    start_node.world_offset = (0, 0)
    start_node.bounds = (0, 0, start_node.shape_width() - 1, start_node.shape_height() - 1)
    layout.nodes.append(start_node)
    layout.start_node = start_node

    frontier = [start_node]
    next_id = 1

    while len(layout.nodes) < room_count and frontier:
        parent = rng.choice(frontier)
        directions = list(DIRECTIONS.items())
        rng.shuffle(directions)

        placed = False
        for direction_name, (dx, dy) in directions:
            if direction_name in parent.connections:
                continue

            candidate_shape = _generate_capped_shape(rng, room_radius, feature_chance, max_features)
            new_node = RoomNode(next_id, room_type=ROOM_TYPE_NORMAL)
            new_node.shape = candidate_shape

            success = _try_place_room(rng, layout, parent, direction_name, new_node)
            if success:
                width = rng.randint(CORRIDOR_MIN_WIDTH, CORRIDOR_MAX_WIDTH)
                new_node.connections[OPPOSITE[direction_name]] = parent
                parent.connections[direction_name] = new_node
                new_node.connection_widths[OPPOSITE[direction_name]] = width
                parent.connection_widths[direction_name] = width
                layout.nodes.append(new_node)
                frontier.append(new_node)
                next_id += 1
                placed = True
                break

        if not placed:
            frontier.remove(parent)

    _add_extra_connections(rng, layout, extra_connection_chance)

    end_node = _find_farthest_node(layout.start_node)
    end_node.room_type = ROOM_TYPE_END
    end_node.shape = generate_square_room(7, 7)
    _recompute_bounds_for_end_room(end_node)
    layout.end_node = end_node

    for node in layout.all_nodes():
        if node.room_type == ROOM_TYPE_NORMAL:
            node.room_type = ROOM_TYPE_FIGHT

    _assign_all_doors(layout)

    return layout


def _try_place_room(rng, layout, parent, direction_name, new_node):
    dx, dy = DIRECTIONS[direction_name]

    parent_anchor = _door_anchor_local(parent.shape, direction_name)
    parent_world_anchor = (
        parent.world_offset[0] + parent_anchor[0],
        parent.world_offset[1] + parent_anchor[1],
    )

    new_anchor_local = _door_anchor_local(new_node.shape, OPPOSITE[direction_name])

    for attempt in range(8):
        corridor_length = rng.randint(CORRIDOR_MIN_LENGTH, CORRIDOR_MAX_LENGTH) + attempt * 3

        target_anchor_x = parent_world_anchor[0] + dx * corridor_length
        target_anchor_y = parent_world_anchor[1] + dy * corridor_length

        offset_x = target_anchor_x - new_anchor_local[0]
        offset_y = target_anchor_y - new_anchor_local[1]

        w = new_node.shape_width()
        h = new_node.shape_height()
        candidate_bounds = (offset_x, offset_y, offset_x + w - 1, offset_y + h - 1)

        if any(_bounds_overlap(candidate_bounds, other.bounds) for other in layout.all_nodes()):
            continue

        # le trajet du couloir lui-même ne doit traverser aucune AUTRE salle
        path_margin = 4
        path_bounds = (
            min(parent_world_anchor[0], target_anchor_x) - path_margin,
            min(parent_world_anchor[1], target_anchor_y) - path_margin,
            max(parent_world_anchor[0], target_anchor_x) + path_margin,
            max(parent_world_anchor[1], target_anchor_y) + path_margin,
        )
        path_blocked = any(
            _bounds_overlap(path_bounds, other.bounds, buffer=0)
            for other in layout.all_nodes()
            if other is not parent
        )
        if path_blocked:
            continue

        new_node.world_offset = (offset_x, offset_y)
        new_node.bounds = candidate_bounds
        return True

    return False


def _recompute_bounds_for_end_room(node):
    old_cx = (node.bounds[0] + node.bounds[2]) // 2
    old_cy = (node.bounds[1] + node.bounds[3]) // 2
    w = node.shape_width()
    h = node.shape_height()
    offset_x = old_cx - w // 2
    offset_y = old_cy - h // 2
    node.world_offset = (offset_x, offset_y)
    node.bounds = (offset_x, offset_y, offset_x + w - 1, offset_y + h - 1)


def _add_extra_connections(rng, layout, extra_connection_chance):
    nodes = layout.all_nodes()
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if any(b is n for n in a.connections.values()):
                continue
            if rng.random() > extra_connection_chance:
                continue

            direction = _infer_direction(a, b)
            if direction is None:
                continue
            if direction in a.connections or OPPOSITE[direction] in b.connections:
                continue

            path_bounds = _path_bounding_box(a, b)
            blocked = any(
                _bounds_overlap(path_bounds, other.bounds, buffer=0)
                for other in nodes if other is not a and other is not b
            )
            if blocked:
                continue

            width = rng.randint(CORRIDOR_MIN_WIDTH, CORRIDOR_MAX_WIDTH)
            a.connections[direction] = b
            b.connections[OPPOSITE[direction]] = a
            a.connection_widths[direction] = width
            b.connection_widths[OPPOSITE[direction]] = width


def _infer_direction(a, b):
    acx = (a.bounds[0] + a.bounds[2]) / 2
    acy = (a.bounds[1] + a.bounds[3]) / 2
    bcx = (b.bounds[0] + b.bounds[2]) / 2
    bcy = (b.bounds[1] + b.bounds[3]) / 2

    dx = bcx - acx
    dy = bcy - acy

    if abs(dx) > abs(dy) * 1.5:
        return "east" if dx > 0 else "west"
    elif abs(dy) > abs(dx) * 1.5:
        return "south" if dy > 0 else "north"
    return None


def _path_bounding_box(a, b):
    ax = (a.bounds[0] + a.bounds[2]) / 2
    ay = (a.bounds[1] + a.bounds[3]) / 2
    bx = (b.bounds[0] + b.bounds[2]) / 2
    by = (b.bounds[1] + b.bounds[3]) / 2
    return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def _find_farthest_node(start_node):
    visited = {start_node.id: start_node}
    queue = [(start_node, 0)]
    farthest_node = start_node
    farthest_dist = 0

    while queue:
        current, dist = queue.pop(0)
        if dist > farthest_dist:
            farthest_dist = dist
            farthest_node = current
        for neighbor in current.connections.values():
            if neighbor.id not in visited:
                visited[neighbor.id] = neighbor
                queue.append((neighbor, dist + 1))

    return farthest_node


def _assign_all_doors(layout):
    for node in layout.all_nodes():
        for direction, neighbor in node.connections.items():
            local_point = _door_anchor_local(node.shape, direction)
            world_x = node.world_offset[0] + local_point[0]
            world_y = node.world_offset[1] + local_point[1]
            width = node.connection_widths[direction]
            node.doors[direction] = (world_x, world_y, width)