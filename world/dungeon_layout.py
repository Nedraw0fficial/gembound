import random

ROOM_TYPE_START = "start"
ROOM_TYPE_END = "end"
ROOM_TYPE_FIGHT = "fight"
ROOM_TYPE_NORMAL = "normal"
#shops TBA : Forger, Enchanted, Trader


DIRECTIONS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


class RoomNode:

    def __init__(self, node_id, cell_x, cell_y, room_type=ROOM_TYPE_NORMAL):
        self.id = node_id
        self.cell_x = cell_x
        self.cell_y = cell_y
        self.room_type = room_type

        self.shape = None
        self.world_offset = None
        self.bounds = None

        self.connections = {}

        self.is_cleared = False
        self.doors_open = True


class DungeonLayout:
    def __init__(self):
        self.nodes = {}
        self.start_node = None
        self.end_node = None

    def get_node_at(self, cell_x, cell_y):
        return self.nodes.get((cell_x, cell_y))

    def all_nodes(self):
        return list(self.nodes.values())


def generate_dungeon_layout(rng, room_count=6, extra_connection_chance=0.15):
    layout = DungeonLayout()

    start_id = 0
    start_node = RoomNode(start_id, 0, 0, room_type=ROOM_TYPE_START)
    layout.nodes[(0, 0)] = start_node
    layout.start_node = start_node

    frontier = [start_node]
    next_id = 1

    while len(layout.nodes) < room_count and frontier:
        parent = rng.choice(frontier)
        directions = list(DIRECTIONS.items())
        rng.shuffle(directions)

        placed = False
        for direction_name, (dx, dy) in directions:
            new_cell = (parent.cell_x + dx, parent.cell_y + dy)
            if new_cell in layout.nodes:
                continue

            new_node = RoomNode(next_id, new_cell[0], new_cell[1], room_type=ROOM_TYPE_NORMAL)
            layout.nodes[new_cell] = new_node
            next_id += 1

            parent.connections[direction_name] = new_node
            new_node.connections[OPPOSITE[direction_name]] = parent

            frontier.append(new_node)
            placed = True
            break

        if not placed:
            frontier.remove(parent)

    #intersections
    all_cells = list(layout.nodes.keys())
    for (cx, cy) in all_cells:
        node = layout.nodes[(cx, cy)]
        for direction_name, (dx, dy) in DIRECTIONS.items():
            if direction_name in node.connections:
                continue
            neighbor_cell = (cx + dx, cy + dy)
            neighbor = layout.nodes.get(neighbor_cell)
            if neighbor is None:
                continue
            if OPPOSITE[direction_name] in neighbor.connections:
                continue
            if rng.random() < extra_connection_chance:
                node.connections[direction_name] = neighbor
                neighbor.connections[OPPOSITE[direction_name]] = node

    #end
    end_node = _find_farthest_node(layout.start_node)
    end_node.room_type = ROOM_TYPE_END
    layout.end_node = end_node

    for node in layout.all_nodes():
        if node.room_type == ROOM_TYPE_NORMAL:
            node.room_type = ROOM_TYPE_FIGHT

    return layout


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