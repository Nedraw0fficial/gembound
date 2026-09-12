import socket
import selectors
import config
from network.protocol import (
    decode, encode,
    make_state_message, make_world_message, make_welcome_message,
    make_chat_broadcast, make_notice_message, make_full_message,
    MSG_INPUT, MSG_JOIN, MSG_CHAT,
)
from network.discovery import Announcer
from world.room_shape import generate_room_shape
from world.dungeon_autotile import autotile_room
from world.dungeon_tiles import get_spawn_positions
from entities.player import new_player_state, update_player

HOST_PORT = 5555
HOST_SESSION_ID = 0
HOST_SLOT = 0

ROOM_RADIUS = 8
ROOM_MARGIN = 4


class Host:
    def __init__(self, pseudo="Hôte", seed=None, max_players=4, save_name="Sans nom"):
        self.sel = selectors.DefaultSelector()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setblocking(False)
        self.server_sock.bind(("0.0.0.0", HOST_PORT))
        self.server_sock.listen()
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        import random
        rng = random.Random(seed)
        shape = generate_room_shape(rng, radius=ROOM_RADIUS)
        max_x = max(x for x, y in shape)
        max_y = max(y for x, y in shape)
        ground_positions = [(x + ROOM_MARGIN, y + ROOM_MARGIN) for x, y in shape]
        self.room = autotile_room(
            ground_positions,
            width=max_x + ROOM_MARGIN * 2 + 1,
            height=max_y + ROOM_MARGIN * 2 + 1,
        )

        spawn_tiles = get_spawn_positions(self.room, max_players)

        self.available_slots = list(range(1, max_players))

        self.clients = {}
        self.next_session_id = 1

        host_x, host_y = spawn_tiles[HOST_SLOT]
        self.players = {
            HOST_SESSION_ID: new_player_state(host_x * config.TILE_SIZE, host_y * config.TILE_SIZE)
        }
        self.pseudos = {
            HOST_SESSION_ID: pseudo
        }
        self._spawn_tiles = spawn_tiles

        self.messages = []

        self.max_players = max_players
        self.save_name = save_name
        self.announcer = Announcer()

    def poll_network(self):
        events = self.sel.select(timeout=0)
        for key, mask in events:
            if key.data is None:
                self._accept_connection()
            else:
                self._read_client(key.data)

    def _accept_connection(self):
        conn, addr = self.server_sock.accept()

        if not self.available_slots:
            print(f"[HOST] Connexion refusée depuis {addr} (partie pleine)")
            try:
                conn.send(encode(make_full_message("Partie pleine")))
            except OSError:
                pass
            conn.close()
            return

        conn.setblocking(False)
        session_id = self.next_session_id
        self.next_session_id += 1
        slot = self.available_slots.pop(0)

        self.clients[session_id] = {
            "conn": conn,
            "recv_buffer": "",
            "keys": {"up": False, "down": False, "left": False, "right": False},
            "slot": slot,
        }
        self.pseudos[session_id] = f"Joueur {session_id}"

        spawn_x, spawn_y = self._spawn_tiles[slot]
        self.players[session_id] = new_player_state(spawn_x * config.TILE_SIZE, spawn_y * config.TILE_SIZE)

        self.sel.register(conn, selectors.EVENT_READ, data=session_id)
        print(f"[HOST] Client {session_id} connecté depuis {addr} (slot {slot})")

        conn.send(encode(make_welcome_message(session_id)))
        conn.send(encode(make_world_message(self.room.to_dict())))

    def _read_client(self, session_id):
        client = self.clients[session_id]
        try:
            data = client["conn"].recv(65536)
        except BlockingIOError:
            return
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self._disconnect_client(session_id)
            return

        if not data:
            self._disconnect_client(session_id)
            return

        client["recv_buffer"] += data.decode("utf-8")
        while "\n" in client["recv_buffer"]:
            line, client["recv_buffer"] = client["recv_buffer"].split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))

            if message["type"] == MSG_INPUT:
                client["keys"] = message["keys"]
            elif message["type"] == MSG_JOIN:
                pseudo = message["pseudo"]
                self.pseudos[session_id] = pseudo
                print(f"[HOST] Client {session_id} a choisi le pseudo '{pseudo}'")
                self._broadcast_notice(f"{pseudo} a rejoint la partie.")
            elif message["type"] == MSG_CHAT:
                pseudo = self.pseudos.get(session_id, "???")
                self._broadcast_chat(pseudo, message["text"])

    def _disconnect_client(self, session_id):
        pseudo = self.pseudos.get(session_id, "???")
        print(f"[HOST] Client {session_id} déconnecté")
        self.sel.unregister(self.clients[session_id]["conn"])
        self.available_slots.append(self.clients[session_id]["slot"])
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
            self._disconnect_client(session_id)

    def send_chat(self, text):
        self._broadcast_chat(self.pseudos[HOST_SESSION_ID], text)

    def update(self, dt, host_keys):
        update_player(self.players[HOST_SESSION_ID], host_keys, dt, self.room)
        for session_id, client in self.clients.items():
            update_player(self.players[session_id], client["keys"], dt, self.room)

    def broadcast_state(self):
        if not self.clients:
            return
        self._send_to_all(encode(make_state_message(self.players, self.pseudos)))

    def tick_announcer(self, dt):
        info = {
            "pseudo": self.pseudos[HOST_SESSION_ID],
            "save_name": self.save_name,
            "current_players": 1 + len(self.clients),
            "max_players": self.max_players,
        }
        self.announcer.tick(dt, info)

    def close(self):
        self.announcer.close()