import socket
from network.protocol import (
    decode, encode, make_input_message, make_join_message, make_chat_request,
    MSG_STATE, MSG_WORLD, MSG_WELCOME, MSG_CHAT, MSG_NOTICE, MSG_FULL,
)
from world.dungeon_tiles import DungeonRoom
from entities.gate import gate_from_dict

HOST_PORT = 5555


class Client:
    def __init__(self, host_ip, pseudo="Joueur"):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.sock.settimeout(5)
            self.sock.connect((host_ip, HOST_PORT))
            self.sock.settimeout(None)
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self.sock.close()
            raise ConnectionError(
                f"Impossible de rejoindre l'hôte {host_ip}:{HOST_PORT}"
            ) from e

        self.sock.setblocking(False)

        self.recv_buffer = ""
        self.players = {}
        self.pseudos = {}
        self.room = None
        self.session_id = None

        self.pseudo = pseudo
        self._joined = False
        self.rejected_reason = None

        self.messages = []

    def send_input(self, keys_pressed):
        if self.rejected_reason:
            return
        message = encode(make_input_message(keys_pressed))
        try:
            self.sock.send(message)
        except BlockingIOError:
            pass
        except (ConnectionResetError, OSError):
            self.rejected_reason = self.rejected_reason or "Connexion perdue"

    def send_chat(self, text):
        if self.rejected_reason:
            return
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
            print("[CLIENT] Déconnecté de l'hôte")
            return

        self.recv_buffer += data.decode("utf-8")
        while "\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))

            if message["type"] == MSG_WELCOME:
                self.session_id = message["session_id"]
                print(f"[CLIENT] ID de session reçu : {self.session_id}")
                self._send_join()
            elif message["type"] == MSG_STATE:
                self.players = {int(k): v for k, v in message["players"].items()}
                self.pseudos = {int(k): v for k, v in message["pseudos"].items()}
            elif message["type"] == MSG_WORLD:
                self.room = DungeonRoom.from_dict(message["tilemap"])
                self.room_bounds = message["room_bounds"]
                self.gates = [gate_from_dict(g) for g in message["gates"]]
                print("[CLIENT] Donjon reçu")
            elif message["type"] == MSG_CHAT:
                self.messages.append({"kind": "chat", "pseudo": message["pseudo"], "text": message["text"]})
            elif message["type"] == MSG_NOTICE:
                self.messages.append({"kind": "notice", "text": message["text"]})
            elif message["type"] == MSG_FULL:
                self.rejected_reason = message["reason"]

    def _send_join(self):
        if self._joined:
            return
        message = encode(make_join_message(self.pseudo))
        try:
            self.sock.send(message)
            self._joined = True
        except BlockingIOError:
            pass