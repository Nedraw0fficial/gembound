import random
from world.dungeon_layout import generate_dungeon_layout
from world.dungeon_corridors import generate_corridor_positions
from world.dungeon_autotile import autotile_room


class DungeonFloor:
    """étage complet"""

    def __init__(self, layout, room):
        self.layout = layout
        self.room = room

    def find_room_at(self, tile_x, tile_y):
        """Retourne le RoomNode dont les bounds contiennent cette position
        ou None si le joueur est dans un couloir"""
        for node in self.layout.all_nodes():
            min_x, min_y, max_x, max_y = node.bounds
            if min_x <= tile_x <= max_x and min_y <= tile_y <= max_y:
                return node
        return None


def generate_dungeon_floor(seed=None, room_count=6):
    rng = random.Random(seed)

    layout = generate_dungeon_layout(rng, room_count=room_count)
    corridor_cells = generate_corridor_positions(rng, layout)

    all_ground = set(corridor_cells)
    for node in layout.all_nodes():
        offset_x, offset_y = node.world_offset
        for (lx, ly) in node.shape:
            all_ground.add((offset_x + lx, offset_y + ly))

    min_x = min(x for x, y in all_ground)
    min_y = min(y for x, y in all_ground)
    max_x = max(x for x, y in all_ground)
    max_y = max(y for x, y in all_ground)

    margin = 4
    shifted_ground = [(x - min_x + margin, y - min_y + margin) for x, y in all_ground]

    width = (max_x - min_x) + margin * 2 + 1
    height = (max_y - min_y) + margin * 2 + 1

    room = autotile_room(shifted_ground, width, height)

    #décale aussi les métadonnées de layout pour qu'elles matchent le
    #système de coordonnées final de la DungeonRoom
    for node in layout.all_nodes():
        ox, oy = node.world_offset
        node.world_offset = (ox - min_x + margin, oy - min_y + margin)
        bx0, by0, bx1, by1 = node.bounds
        node.bounds = (bx0 - min_x + margin, by0 - min_y + margin, bx1 - min_x + margin, by1 - min_y + margin)
        node.doors = {
            direction: (dx - min_x + margin, dy - min_y + margin, width)
            for direction, (dx, dy, width) in node.doors.items()
        }

    return DungeonFloor(layout, room)