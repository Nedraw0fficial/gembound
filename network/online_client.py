import socket
from network.protocol import (
    decode, encode,
    make_lobby_list_request, make_create_lobby_message, make_join_lobby_message,
    MSG_LOBBY_LIST, MSG_LOBBY_ERROR,
    MSG_WELCOME, MSG_STATE, MSG_WORLD, MSG_CHAT, MSG_NOTICE, MSG_FULL,
)
from world.dungeon_tiles import DungeonRoom

DEFAULT_SERVER_HOST = "89.168.61.135"#OracleServer
DEFAULT_SERVER_PORT = 5560


class OnlineClient:
    def __init__(self, pseudo, server_host=DEFAULT_SERVER_HOST, server_port=DEFAULT_SERVER_PORT):
        self.pseudo = pseudo
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_host, server_port))
        self.sock.setblocking(False)

        self.recv_buffer = ""

        #repo
        self.lobby_list = []
        self.lobby_error = None
        self.joined_lobby = False

        #ingame
        self.players = {}
        self.pseudos = {}
        self.room = None
        self.session_id = None
        self.messages = []
        self.rejected_reason = None

    def request_lobby_list(self):
        try:
            self.sock.send(encode(make_lobby_list_request()))
        except BlockingIOError:
            pass

    def create_lobby(self, name, seed, max_players, password):
        try:
            self.sock.send(encode(make_create_lobby_message(self.pseudo, name, seed, max_players, password)))
        except BlockingIOError:
            pass

    def join_lobby(self, lobby_id, password=""):
        try:
            self.sock.send(encode(make_join_lobby_message(self.pseudo, lobby_id, password)))
        except BlockingIOError:
            pass

    def send_input(self, keys_pressed):
        if not self.joined_lobby or self.rejected_reason:
            return
        from network.protocol import make_input_message
        try:
            self.sock.send(encode(make_input_message(keys_pressed)))
        except BlockingIOError:
            pass
        except (ConnectionResetError, OSError):
            self.rejected_reason = self.rejected_reason or "Connexion perdue"

    def send_chat(self, text):
        if not self.joined_lobby or self.rejected_reason:
            return
        from network.protocol import make_chat_request
        try:
            self.sock.send(encode(make_chat_request(text)))
        except BlockingIOError:
            pass
        except (ConnectionResetError, OSError):
            self.rejected_reason = self.rejected_reason or "Connexion perdue"

    def poll_network(self):
        try:
            data = self.sock.recv(65536)
        except BlockingIOError:
            return
        except (ConnectionResetError, OSError):
            self.rejected_reason = self.rejected_reason or "Connexion perdue"
            return

        if not data:
            self.rejected_reason = self.rejected_reason or "Déconnecté du serveur"
            return

        self.recv_buffer += data.decode("utf-8")
        while "\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))
            self._handle_message(message)

    def _handle_message(self, message):
        msg_type = message["type"]

        if msg_type == MSG_LOBBY_LIST:
            self.lobby_list = message["lobbies"]
        elif msg_type == MSG_LOBBY_ERROR:
            self.lobby_error = message["reason"]
        elif msg_type == MSG_WELCOME:
            self.session_id = message["session_id"]
            self.joined_lobby = True
        elif msg_type == MSG_STATE:
            self.players = {int(k): v for k, v in message["players"].items()}
            self.pseudos = {int(k): v for k, v in message["pseudos"].items()}
        elif msg_type == MSG_WORLD:
            self.room = DungeonRoom.from_dict(message["tilemap"])
        elif msg_type == MSG_CHAT:
            self.messages.append({"kind": "chat", "pseudo": message["pseudo"], "text": message["text"]})
        elif msg_type == MSG_NOTICE:
            self.messages.append({"kind": "notice", "text": message["text"]})
        elif msg_type == MSG_FULL:
            self.rejected_reason = message["reason"]

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass