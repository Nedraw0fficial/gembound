from server.lobby import Lobby

MAX_LOBBIES = 1024
MAX_LOBBIES_PER_CREATOR = 8


class LobbyManager:
    def __init__(self):
        self.lobbies = {}
        self.next_lobby_id = 1

    def create_lobby(self, name, seed, max_players, password, creator_pseudo, creator_key):
        if len(self.lobbies) >= MAX_LOBBIES:
            return None, "Serveur plein, réessaie plus tard."

        creator_count = sum(1 for l in self.lobbies.values() if l.creator_key == creator_key)
        if creator_count >= MAX_LOBBIES_PER_CREATOR:
            return None, "Tu as déjà atteint ta limite de lobbies créés."

        lobby_id = self.next_lobby_id
        self.next_lobby_id += 1
        lobby = Lobby(lobby_id, name, seed, max_players, password, creator_pseudo, creator_key)
        self.lobbies[lobby_id] = lobby
        return lobby, None

    def get_lobby(self, lobby_id):
        return self.lobbies.get(lobby_id)

    def list_summaries(self):
        return [lobby.summary() for lobby in self.lobbies.values()]

    def remove_empty_lobbies(self):
        """Ferme les lobbies vides pour libérer la précieuse mémoire"""
        empty_ids = [
            lobby_id for lobby_id, lobby in self.lobbies.items()
            if lobby.started and lobby.current_player_count == 0
        ]
        for lobby_id in empty_ids:
            del self.lobbies[lobby_id]


