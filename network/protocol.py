import json

#types de data
MSG_INPUT = "input"#clientToHost
MSG_STATE = "state"#hostToClient
MSG_WORLD = "world"#world HtC
MSG_JOIN = "join"#connexion CtH
MSG_WELCOME = "welcome"#id HtC
MSG_CHAT = "chat"#chat CtH
MSG_NOTICE = "notice"#notifs HtC
MSG_FULL = "full"#serveur full HtC


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

def make_world_message(tilemap_dict):
    """
    One-time (monde)
    """
    return {
        "type": MSG_WORLD,
        "tilemap": tilemap_dict
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