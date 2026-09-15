import socket
import selectors
import time
from network.protocol import (
    decode, encode,
    make_lobby_list_message, make_lobby_error_message,
    MSG_LOBBY_LIST_REQUEST, MSG_CREATE_LOBBY, MSG_JOIN_LOBBY,
)
from server.lobby_manager import LobbyManager

SERVER_PORT = 5560
TICK_RATE = 1 / 30  #30updt par s


class DedicatedServer:
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.lobby_manager = LobbyManager()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("0.0.0.0", SERVER_PORT))
        self.server_sock.listen()
        self.server_sock.setblocking(False)
        self.sel.register(self.server_sock, selectors.EVENT_READ, data="listener")

        # conn -> état : soit en attente
        # soit attaché à un lobby (+session_id)
        self.connections = {}

    def run(self):
        print(f"[SERVER] Démarré sur le port {SERVER_PORT}")
        last_tick = time.monotonic()
        while True:
            events = self.sel.select(timeout=TICK_RATE)
            for key, mask in events:
                if key.data == "listener":
                    self._accept_connection()
                else:
                    self._read_connection(key.fileobj)

            now = time.monotonic()
            dt = now - last_tick
            last_tick = now
            self._tick_all_lobbies(dt)

    def _accept_connection(self):
        conn, addr = self.server_sock.accept()
        conn.setblocking(False)
        self.connections[conn] = {"recv_buffer": "", "lobby_id": None, "session_id": None}
        self.sel.register(conn, selectors.EVENT_READ, data=conn)
        print(f"[SERVER] Connexion depuis {addr}")

    def _read_connection(self, conn):
        state = self.connections.get(conn)
        if state is None:
            return

        if state["lobby_id"] is not None:
            lobby = self.lobby_manager.get_lobby(state["lobby_id"])
            if lobby is None:
                self._close_connection(conn)
                return
            ok = lobby.session.read_client(state["session_id"])
            if not ok:
                lobby.session.disconnect_player(state["session_id"])
                self._close_connection(conn)
            return

        try:
            data = conn.recv(65536)
        except BlockingIOError:
            return
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self._close_connection(conn)
            return

        if not data:
            self._close_connection(conn)
            return

        state["recv_buffer"] += data.decode("utf-8")
        while "\n" in state["recv_buffer"]:
            line, state["recv_buffer"] = state["recv_buffer"].split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))
            self._handle_pending_message(conn, state, message)

    def _handle_pending_message(self, conn, state, message):
        msg_type = message["type"]

        if msg_type == MSG_LOBBY_LIST_REQUEST:
            summaries = self.lobby_manager.list_summaries()
            conn.send(encode(make_lobby_list_message(summaries)))

        elif msg_type == MSG_CREATE_LOBBY:
            lobby = self.lobby_manager.create_lobby(
                name=message["name"],
                seed=message["seed"],
                max_players=message["max_players"],
                password=message["password"],
                creator_pseudo=message["pseudo"],
            )
            self._join_lobby(conn, state, lobby, message["pseudo"])

        elif msg_type == MSG_JOIN_LOBBY:
            lobby = self.lobby_manager.get_lobby(message["lobby_id"])
            if lobby is None:
                conn.send(encode(make_lobby_error_message("Lobby introuvable.")))
                return
            if not lobby.check_password(message["password"]):
                conn.send(encode(make_lobby_error_message("Mot de passe incorrect.")))
                return
            if lobby.is_full:
                conn.send(encode(make_lobby_error_message("Lobby plein.")))
                return
            self._join_lobby(conn, state, lobby, message["pseudo"])

    def _join_lobby(self, conn, state, lobby, pseudo):
        session_id = lobby.session.add_player(conn, pseudo)
        lobby.started = True
        state["lobby_id"] = lobby.id
        state["session_id"] = session_id

    def _close_connection(self, conn):
        try:
            self.sel.unregister(conn)
        except KeyError:
            pass
        self.connections.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass

    def _tick_all_lobbies(self, dt):
        for lobby in list(self.lobby_manager.lobbies.values()):
            lobby.session.update(dt)
            lobby.session.broadcast_state()
        self.lobby_manager.remove_empty_lobbies()


if __name__ == "__main__":
    server = DedicatedServer()
    server.run()