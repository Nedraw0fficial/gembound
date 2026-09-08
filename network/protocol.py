import json

#types de msg
MSG_INPUT = "input"#clientToHost
MSG_STATE = "state"#hostToClient


def make_input_message(keys_pressed):
    """
    Le client construit ce message à chaque frame pour dire à l'hôte
    quelles touches sont actuellement pressées.
    keys_pressed : dict du style {"up": True, "down": False, "left": False, "right": True}
    """
    return {
        "type": MSG_INPUT,
        "keys": keys_pressed
    }


def make_state_message(players):
    """
    L'hôte construit ce message pour dire à tout le monde où sont les joueurs.
    players : dict du style {"host": {"x": 100, "y": 200}, "client": {"x": 150, "y": 220}}
    """
    return {
        "type": MSG_STATE,
        "players": players
    }


def encode(message):
    """Transforme un dict Python en bytes prêts à envoyer sur le réseau."""
    return (json.dumps(message) + "\n").encode("utf-8")

def decode(raw_bytes):
    """Transforme des bytes reçus en dict Python."""
    return json.loads(raw_bytes.decode("utf-8"))