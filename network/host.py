import socket
import selectors
import config
from network.protocol import decode, encode, make_state_message, MSG_INPUT

HOST_PORT = 5555


class Host:
    def __init__(self):
        self.sel = selectors.DefaultSelector()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setblocking(False)
        self.server_sock.bind(("0.0.0.0", HOST_PORT))
        self.server_sock.listen()
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        self.client_conn = None       #cleint socket
        self.recv_buffer = ""         #received txt

        #gamestate
        self.players = {
            "host": {"x": 400.0, "y": 300.0},
            "client": {"x": 500.0, "y": 300.0},
        }
        self.client_keys = {"up": False, "down": False, "left": False, "right": False}

    def poll_network(self):
        """Check liste attente sans bloquer"""
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

    def _read_client(self):
        try:
            data = self.client_conn.recv(4096)
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
        """Avance la simulation d'un pas de temps dt (s)"""
        self._move_player("host", host_keys, dt)
        self._move_player("client", self.client_keys, dt)

    def _move_player(self, name, keys, dt):
        p = self.players[name]
        if keys.get("up"):
            p["y"] -= config.PLAYER_SPEED * dt
        if keys.get("down"):
            p["y"] += config.PLAYER_SPEED * dt
        if keys.get("left"):
            p["x"] -= config.PLAYER_SPEED * dt
        if keys.get("right"):
            p["x"] += config.PLAYER_SPEED * dt

    def broadcast_state(self):
        if self.client_conn is None:
            return
        message = encode(make_state_message(self.players))
        try:
            self.client_conn.send(message)
        except BlockingIOError:
            pass  # tampon d'envoi plein -> retentep rochaine frame