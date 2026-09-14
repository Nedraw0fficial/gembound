import socket
import json
import time

BROADCAST_PORT = 5556
ANNOUNCE_INTERVAL = 1.0
GAME_TIMEOUT = 3.0


class Announcer:
    """Côté hôte : diffuse périodiquement la présence de la partie sur le réseau local."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        self._time_since_last = ANNOUNCE_INTERVAL

    def tick(self, dt, info):
        """info : dict avec pseudo, save_name, current_players, max_players."""
        self._time_since_last += dt
        if self._time_since_last < ANNOUNCE_INTERVAL:
            return
        self._time_since_last = 0.0
        try:
            payload = json.dumps(info).encode("utf-8")
            self.sock.sendto(payload, ("<broadcast>", BROADCAST_PORT))
        except OSError:
            pass  # réseau temporairement indisponible, on retentera au prochain tick

    def close(self):
        self.sock.close()


class Listener:
    """Côté client : écoute les annonces et maintient la liste des parties visibles."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", BROADCAST_PORT))
        self.sock.setblocking(False)
        self.games = {} # ip -> {"pseudo", "save_name", "current_players", "max_players", "last_seen"}

    def poll(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                print(f"[DISCOVERY] Partie trouvée depuis {addr[0]}")
            except BlockingIOError:
                break
            try:
                info = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            ip = addr[0]
            info["ip"] = ip
            info["last_seen"] = time.monotonic()
            self.games[ip] = info

        now = time.monotonic()
        expired = [ip for ip, g in self.games.items() if now - g["last_seen"] > GAME_TIMEOUT]
        for ip in expired:
            del self.games[ip]

    def close(self):
        self.sock.close()