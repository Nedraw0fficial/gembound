import json

#types de data
MSG_INPUT = "input"#clientToHost
MSG_STATE = "state"#hostToClient
MSG_WORLD = "world"#world HtC



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
    Pos des joueurs envoyés
    """
    return {
        "type": MSG_STATE,
        "players": players
    }

def make_world_message(tilemap_dict):
    """
    One-time (monde)
    """
    return {
        "type": MSG_WORLD,
        "tilemap": tilemap_dict
    }


def encode(message):
    """Transforme un dict Python en bytes prêts à envoyer sur le réseau."""
    return (json.dumps(message) + "\n").encode("utf-8")

def decode(raw_bytes):
    """Transforme des bytes reçus en dict Python."""
    return json.loads(raw_bytes.decode("utf-8"))