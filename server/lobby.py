from server.game_session import GameSession


class Lobby:
    def __init__(self, lobby_id, name, seed, max_players, password, creator_pseudo):
        self.id = lobby_id
        self.name = name
        self.max_players = max_players
        self.password = password
        self.creator_pseudo = creator_pseudo

        self.session = GameSession(seed=seed, max_players=max_players)
        self.started = False # passe à True dès qu'au moins un joueur est dedans

    @property
    def current_player_count(self):
        return self.session.current_player_count

    @property
    def is_full(self):
        return self.session.is_full

    @property
    def has_password(self):
        return bool(self.password)

    def check_password(self, attempt):
        return not self.password or attempt == self.password

    def summary(self):
        """Format compact"""
        return {
            "id": self.id,
            "name": self.name,
            "current_players": self.current_player_count,
            "max_players": self.max_players,
            "has_password": self.has_password,
        }