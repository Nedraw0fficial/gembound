import socket
from network.protocol import decode, encode, make_input_message, MSG_STATE

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

    def send_input(self, keys_pressed):
        """keys_pressed : dict {"up": bool, "down": bool, "left": bool, "right": bool}"""
        message = encode(make_input_message(keys_pressed))
        try:
            self.sock.send(message)
        except BlockingIOError:
            pass  #tampon plein

    def poll_network(self):
        """Read host state"""
        try:
            data = self.sock.recv(4096)
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