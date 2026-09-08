import socket
import selectors
import config
from network.protocol import decode, encode, make_state_message, make_world_message, MSG_INPUT
from world.worldgen import generate_island, find_spawn_point
from entities.player import new_player_state, update_player

HOST_PORT = 5555


class Host:
    def __init__(self):
        self.sel = selectors.DefaultSelector()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setblocking(False)
        self.server_sock.bind(("0.0.0.0", HOST_PORT))
        self.server_sock.listen()
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        self.client_conn = None
        self.recv_buffer = ""

        #island gen
        self.tilemap = generate_island(config.WORLD_WIDTH, config.WORLD_HEIGHT)

        spawn_x, spawn_y = find_spawn_point(self.tilemap)
        spawn_px = spawn_x * config.TILE_SIZE
        spawn_py = spawn_y * config.TILE_SIZE

        self.players = {
            "host": new_player_state(spawn_px, spawn_py),
            "client": new_player_state(spawn_px + config.TILE_SIZE, spawn_py),
        }
        self.client_keys = {"up": False, "down": False, "left": False, "right": False}

    def poll_network(self):
        events = self.sel.select(timeout=0)
        for key, mask in events:
            if key.data is None:
                self._accept_connection()
            else:
                self._read_client()

    def _accept_connection(self):
        conn, addr = self.server_sock.accept()
        conn.setblocking(False)
        self.client_conn = conn
        self.sel.register(conn, selectors.EVENT_READ, data="client")
        print(f"[HOST] Client connecté depuis {addr}")

        #share world
        world_message = encode(make_world_message(self.tilemap.to_dict()))
        conn.send(world_message)

    def _read_client(self):
        try:
            data = self.client_conn.recv(65536)
        except BlockingIOError:
            return

        if not data:
            print("[HOST] Client déconnecté")
            self.sel.unregister(self.client_conn)
            self.client_conn = None
            return

        self.recv_buffer += data.decode("utf-8")
        while "\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))
            if message["type"] == MSG_INPUT:
                self.client_keys = message["keys"]

    def update(self, dt, host_keys):
        update_player(self.players["host"], host_keys, dt, self.tilemap)
        update_player(self.players["client"], self.client_keys, dt, self.tilemap)

    def broadcast_state(self):
        if self.client_conn is None:
            return
        message = encode(make_state_message(self.players))
        try:
            self.client_conn.send(message)
        except BlockingIOError:
            pass