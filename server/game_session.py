from network.protocol import (
    decode, encode,
    make_state_message, make_world_message, make_welcome_message,
    make_chat_broadcast, make_notice_message, make_full_message,
    MSG_INPUT, MSG_JOIN, MSG_CHAT,
)
from world.dungeon_floor import generate_dungeon_floor
from world.dungeon_tiles import find_walkable_near
from entities.player import new_player_state, update_player
import config

TILE_SIZE = config.TILE_SIZE

MAX_BUFFER_SIZE = 65536 #~64Ko


class GameSession:
    """
    serveur autoritaire, pas de joueur hsot
    """

    def __init__(self, seed, max_players):
        self.max_players = max_players
        self.floor = generate_dungeon_floor(seed=seed, room_count=6)
        self.room = self.floor.room

        start_bounds = self.floor.layout.start_node.bounds
        center_x = (start_bounds[0] + start_bounds[2]) // 2
        center_y = (start_bounds[1] + start_bounds[3]) // 2
        offsets = [(0, 0), (2, 0), (0, 2), (2, 2)]
        self._spawn_tiles = [
            find_walkable_near(self.room, center_x + dx, center_y + dy)
            for dx, dy in offsets[:max_players]
        ]

        self.available_slots = list(range(max_players))

        self.clients = {}
        self.players = {}
        self.pseudos = {}
        self.messages = []

        self.next_session_id = 0

    @property
    def current_player_count(self):
        return len(self.clients)

    @property
    def is_full(self):
        return not self.available_slots

    def add_player(self, conn, pseudo):
        """Ajoute un nouveau joueur. Retourne son session_id"""
        session_id = self.next_session_id
        self.next_session_id += 1
        slot = self.available_slots.pop(0)

        spawn_x, spawn_y = self._spawn_tiles[slot]
        self.players[session_id] = new_player_state(spawn_x * TILE_SIZE, spawn_y * TILE_SIZE)
        self.pseudos[session_id] = pseudo

        self.clients[session_id] = {
            "conn": conn,
            "recv_buffer": "",
            "keys": {"up": False, "down": False, "left": False, "right": False},
            "slot": slot,
        }

        conn.send(encode(make_welcome_message(session_id)))
        room_bounds = [node.bounds for node in self.floor.layout.all_nodes()]
        conn.send(encode(make_world_message(self.room.to_dict(), room_bounds)))

        self._broadcast_notice(f"{pseudo} a rejoint la partie.")
        return session_id

    def read_client(self, session_id):
        """
        Lit les données disponibles sur le socket de ce joueur
        Retourne False si la connexion doit être fermée
        message anormalement gros = client suspect
        """
        client = self.clients[session_id]
        try:
            data = client["conn"].recv(65536)
        except BlockingIOError:
            return True
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            return False

        if not data:
            return False

        client["recv_buffer"] += data.decode("utf-8")

        if len(client["recv_buffer"]) > MAX_BUFFER_SIZE:
            return False

        while "\n" in client["recv_buffer"]:
            line, client["recv_buffer"] = client["recv_buffer"].split("\n", 1)
            if len(line) > MAX_BUFFER_SIZE:
                return False
            message = decode((line + "\n").encode("utf-8"))
            self._handle_message(session_id, message)

        return True

    def _handle_message(self, session_id, message):
        if message["type"] == MSG_INPUT:
            self.clients[session_id]["keys"] = message["keys"]
        elif message["type"] == MSG_CHAT:
            pseudo = self.pseudos.get(session_id, "???")
            self._broadcast_chat(pseudo, message["text"])

    def disconnect_player(self, session_id):
        pseudo = self.pseudos.get(session_id, "???")
        slot = self.clients[session_id]["slot"]
        self.available_slots.append(slot)
        del self.clients[session_id]
        del self.players[session_id]
        del self.pseudos[session_id]
        self._broadcast_notice(f"{pseudo} a quitté la partie.")

    def _broadcast_chat(self, pseudo, text):
        self.messages.append({"kind": "chat", "pseudo": pseudo, "text": text})
        self._send_to_all(encode(make_chat_broadcast(pseudo, text)))

    def _broadcast_notice(self, text):
        self.messages.append({"kind": "notice", "text": text})
        self._send_to_all(encode(make_notice_message(text)))

    def _send_to_all(self, encoded_message):
        dead_sessions = []
        for session_id, client in self.clients.items():
            try:
                client["conn"].send(encoded_message)
            except BlockingIOError:
                pass
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                dead_sessions.append(session_id)
        for session_id in dead_sessions:
            self.disconnect_player(session_id)

    def update(self, dt):
        for session_id, client in list(self.clients.items()):
            update_player(self.players[session_id], client["keys"], dt, self.room)

    def broadcast_state(self):
        if not self.clients:
            return
        self._send_to_all(encode(make_state_message(self.players, self.pseudos)))

