import socket
from network.protocol import decode, encode, make_input_message, MSG_STATE, MSG_WORLD
from world.tilemap import Tilemap

HOST_PORT = 5555


class Client:
    def __init__(self, host_ip):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host_ip, HOST_PORT))
        self.sock.setblocking(False)

        self.recv_buffer = ""
        self.players = {
            "host": {"x": 400.0, "y": 300.0},
            "client": {"x": 500.0, "y": 300.0},
        }
        self.tilemap = None

    def send_input(self, keys_pressed):
        message = encode(make_input_message(keys_pressed))
        try:
            self.sock.send(message)
        except BlockingIOError:
            pass

    def poll_network(self):
        try:
            data = self.sock.recv(65536)
        except BlockingIOError:
            return

        if not data:
            print("[CLIENT] Déconnecté de l'hôte")
            return

        self.recv_buffer += data.decode("utf-8")
        while "\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))

            if message["type"] == MSG_STATE:
                self.players = message["players"]
            elif message["type"] == MSG_WORLD:
                self.tilemap = Tilemap.from_dict(message["tilemap"])
                print("[CLIENT] Monde reçu")