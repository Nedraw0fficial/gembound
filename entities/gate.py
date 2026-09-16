import config
from world.dungeon_layout import ROOM_TYPE_FIGHT

GATE_STATE_OPEN = "open"
GATE_STATE_CLOSING = "closing"
GATE_STATE_LOCKED = "locked"

CLOSING_FRAME_COUNT = 5
CLOSING_FRAME_DURATION = 0.1 #spf fermeture

_ORIENTATION_BY_DIRECTION = {
    "north": "f",
    "south": "f",
    "west": "l",
    "east": "r",
}


class Gate:
    def __init__(self, room_id, direction, tiles, orientation):
        self.room_id = room_id
        self.direction = direction
        self.tiles = tiles
        self.orientation = orientation
        self.state = GATE_STATE_OPEN
        self.frame_index = 0
        self.frame_timer = 0.0

    def is_solid(self):
        return self.state == GATE_STATE_LOCKED

    def start_closing(self):
        if self.state == GATE_STATE_OPEN:
            self.state = GATE_STATE_CLOSING
            self.frame_index = 0
            self.frame_timer = 0.0

    def open(self):
        self.state = GATE_STATE_OPEN
        self.frame_index = 0
        self.frame_timer = 0.0

    def update(self, dt):
        if self.state != GATE_STATE_CLOSING:
            return
        self.frame_timer += dt
        if self.frame_timer >= CLOSING_FRAME_DURATION:
            self.frame_timer -= CLOSING_FRAME_DURATION
            self.frame_index += 1
            if self.frame_index >= CLOSING_FRAME_COUNT - 1:
                self.frame_index = CLOSING_FRAME_COUNT - 1
                self.state = GATE_STATE_LOCKED

    def world_hitboxes(self):
        """vide si la porte est ouverte"""
        if not self.is_solid():
            return []
        boxes = []
        for (x, y) in self.tiles:
            boxes.append((x * config.TILE_SIZE, y * config.TILE_SIZE, config.TILE_SIZE, config.TILE_SIZE))
        return boxes

    def sprite_key(self):
        if self.state == GATE_STATE_OPEN:
            return ("open", self.orientation, None)
        return ("locked", self.orientation, self.frame_index)


_OFFSET_BY_DIRECTION = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
}


def generate_gates_for_floor(layout):
    gates = []
    for node in layout.all_nodes():
        if node.room_type != ROOM_TYPE_FIGHT:
            continue
        for direction, (anchor_x, anchor_y, width) in node.doors.items():
            orientation = _ORIENTATION_BY_DIRECTION[direction]
            offset_x, offset_y = _OFFSET_BY_DIRECTION[direction]
            anchor_x += offset_x
            anchor_y += offset_y
            half = width // 2

            if direction in ("north", "south"):
                tiles = [(anchor_x - half + i, anchor_y) for i in range(width)]
            else:
                tiles = [(anchor_x, anchor_y - half + i) for i in range(width)]

            gates.append(Gate(node.id, direction, tiles, orientation))

    return gates

def gate_to_dict(gate):
    return {
        "room_id": gate.room_id,
        "direction": gate.direction,
        "tiles": gate.tiles,
        "orientation": gate.orientation,
    }

def gate_from_dict(data):
    return Gate(data["room_id"], data["direction"], [tuple(t) for t in data["tiles"]], data["orientation"])
