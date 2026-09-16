import json

#types de msg
MSG_INPUT = "input"#clientToHost
MSG_STATE = "state"#hostToClient
MSG_WORLD = "world"#world HtC
MSG_JOIN = "join"#connexion CtH
MSG_WELCOME = "welcome"#id HtC
MSG_CHAT = "chat"#chat CtH
MSG_NOTICE = "notice"#notifs HtC
MSG_FULL = "full"#serveur full HtC
MSG_LOBBY_LIST_REQUEST = "lobby_list_request"#CtS
MSG_LOBBY_LIST = "lobby_list"#StC
MSG_CREATE_LOBBY = "create_lobby"#CtServ
MSG_JOIN_LOBBY = "join_lobby"#CtServ
MSG_LOBBY_ERROR = "lobby_error"#StC


def make_lobby_list_request():
    return {"type": MSG_LOBBY_LIST_REQUEST}


def make_lobby_list_message(lobbies):
    """
    list de dict
    [{"id": 0, "name": "Ma partie", "current_players": 1, "max_players": 4,
      "has_password": False}, ...]
    """
    return {"type": MSG_LOBBY_LIST, "lobbies": lobbies}


def make_create_lobby_message(pseudo, name, seed, max_players, password):
    return {
        "type": MSG_CREATE_LOBBY,
        "pseudo": pseudo,
        "name": name,
        "seed": seed,
        "max_players": max_players,
        "password": password,#empty si pas de mdp
    }


def make_join_lobby_message(pseudo, lobby_id, password):
    return {
        "type": MSG_JOIN_LOBBY,
        "pseudo": pseudo,
        "lobby_id": lobby_id,
        "password": password,
    }


def make_lobby_error_message(reason):
    return {"type": MSG_LOBBY_ERROR, "reason": reason}


def make_full_message(reason):
    return {"type": MSG_FULL, "reason": reason}


def make_chat_request(text):
    return {"type": MSG_CHAT, "text": text}


def make_chat_broadcast(pseudo, text):
    return {"type": MSG_CHAT, "pseudo": pseudo, "text": text}


def make_notice_message(text):
    return {"type": MSG_NOTICE, "text": text}

def make_input_message(keys_pressed):
    return {
        "type": MSG_INPUT,
        "keys": keys_pressed
    }


def make_state_message(players, pseudos):
    return {
        "type": MSG_STATE,
        "players": players,
        "pseudos": pseudos,
    }

def make_world_message(tilemap_dict, room_bounds, gates_data):
    """
    One-time (monde)
    """
    return {
        "type": MSG_WORLD,
        "tilemap": tilemap_dict,
        "room_bounds": room_bounds,
        "gates": gates_data,
    }

def make_join_message(pseudo):
    return {
        "type": MSG_JOIN,
        "pseudo": pseudo
    }


def make_welcome_message(session_id):
    return {
        "type": MSG_WELCOME,
        "session_id": session_id
    }


def encode(message):
    """Dict python to bytes"""
    return (json.dumps(message) + "\n").encode("utf-8")

def decode(raw_bytes):
    """bytes to python dict"""
    return json.loads(raw_bytes.decode("utf-8"))