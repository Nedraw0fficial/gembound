from server.lobby import Lobby


class LobbyManager:
    def __init__(self):
        self.lobbies = {}
        self.next_lobby_id = 1

    def create_lobby(self, name, seed, max_players, password, creator_pseudo):
        lobby_id = self.next_lobby_id
        self.next_lobby_id += 1
        lobby = Lobby(lobby_id, name, seed, max_players, password, creator_pseudo)
        self.lobbies[lobby_id] = lobby
        return lobby

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


