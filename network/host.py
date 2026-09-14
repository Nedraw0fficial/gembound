import socket
import selectors
import random
import config
from network.protocol import (
    decode, encode,
    make_state_message, make_world_message, make_welcome_message,
    make_chat_broadcast, make_notice_message, make_full_message,
    MSG_INPUT, MSG_JOIN, MSG_CHAT,
)
from network.discovery import Announcer
from world.room_shape import generate_room_shape
from world.dungeon_autotile import autotile_room
from world.dungeon_tiles import get_spawn_positions, TILE_GROUND, TILE_KEY, TILE_DOOR
from entities.player import new_player_state, update_player, _can_move_to

HOST_PORT = 5555
HOST_SESSION_ID = 0
HOST_SLOT = 0

ROOM_RADIUS = 14
ROOM_MARGIN = 6

QUESTS = [
    {
        "id": "forgotten_guardians",
        "title": "Les gardiens oublies",
        "dialogues": [
            "Le donjon a ete construit pour cacher une force que personne ne devait reveiller.",
            "La cle porte le serment des anciens gardiens.",
            "Quand la porte s'ouvrira, souviens-toi de ceux qui ont protege ce lieu.",
        ],
        "required_npcs": [0, 1, 2],
    },
    {
        "id": "broken_crown",
        "title": "La couronne brisee",
        "dialogues": [
            "Le dernier roi a cache sa couronne derriere cette porte.",
            "Son royaume est tombe quand les salles ont commence a changer.",
            "Ne laisse pas le pouvoir de la couronne choisir ton chemin.",
        ],
        "required_npcs": [0, 2],
    },
    {
        "id": "silent_expedition",
        "title": "L expedition silencieuse",
        "dialogues": [
            "Notre expedition est entree ici il y a cent ans.",
            "Les murs ont efface les noms de nos compagnons.",
            "La porte reconnaitra celui qui se souvient de notre histoire.",
        ],
        "required_npcs": [0, 1, 2],
    },
    {
        "id": "heart_of_stone",
        "title": "Le coeur de pierre",
        "dialogues": [
            "Sous les dalles dort le coeur qui donne sa force au donjon.",
            "La cle n est pas une arme, mais une promesse.",
            "Le coeur ne s ouvrira qu a ceux qui ecoutent les temoins.",
        ],
        "required_npcs": [1, 2],
    },
    {
        "id": "last_message",
        "title": "Le dernier message",
        "dialogues": [
            "Je suis le dernier messager de la cite disparue.",
            "Le message est grave sur la cle, regarde au dela du metal.",
            "Porte ce message jusqu a la prochaine salle.",
        ],
        "required_npcs": [0, 1, 2],
    },
    {
        "id": "sleeping_beast",
        "title": "La bete endormie",
        "dialogues": [
            "Une bete ancienne dort sous le donjon.",
            "Chaque porte ouverte la rapproche du reveil.",
            "Apprends son histoire avant de continuer.",
        ],
        "required_npcs": [0, 1],
    },
    {
        "id": "mirror_path",
        "title": "Le chemin des miroirs",
        "dialogues": [
            "Les salles se repetent, mais aucune n est vraiment identique.",
            "Le donjon observe tes choix depuis les miroirs.",
            "La cle te montrera le passage que tu ne vois pas encore.",
        ],
        "required_npcs": [0, 2],
    },
    {
        "id": "keeper_oath",
        "title": "Le serment du gardien",
        "dialogues": [
            "Un gardien doit connaitre la peur avant de franchir le seuil.",
            "Un gardien doit connaitre la patience avant de prendre la cle.",
            "Un gardien doit connaitre la verite avant d ouvrir la porte.",
        ],
        "required_npcs": [0, 1, 2],
    },
]

NPC_COSTUMES = [
    {"color": [70, 130, 210], "style": "cape"},
    {"color": [150, 85, 175], "style": "hat"},
    {"color": [190, 100, 55], "style": "helmet"},
    {"color": [55, 165, 125], "style": "hood"},
    {"color": [190, 165, 55], "style": "crown"},
    {"color": [150, 65, 75], "style": "mask"},
]

NPC_CHOICES = [
    ["Je vais retrouver la sortie.", "Pourquoi dois-je vous croire ?", "Je veux en savoir plus."],
    ["Je comprends votre histoire.", "Je refuse cette mission.", "Je protegerai le donjon."],
    ["Montrez-moi le chemin.", "Je dois continuer seul.", "Je reviendrai vous aider."],
]


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _make_story(room, spawn_tile, rng=None):
    rng = rng or random.Random()
    quest = rng.choice(QUESTS)
    walkable = [
        (x, y)
        for y in range(room.height)
        for x in range(room.width)
        if room.is_walkable(x, y)
    ]
    door_position = max(walkable, key=lambda tile: _distance(tile, spawn_tile))
    candidates = [tile for tile in walkable if tile != door_position]
    key_position = max(
        candidates,
        key=lambda tile: min(_distance(tile, spawn_tile), _distance(tile, door_position)),
    )
    npc_candidates = [
        tile for tile in candidates
        if tile != key_position and _distance(tile, spawn_tile) >= 4
    ]
    npc_candidates.sort(key=lambda tile: (_distance(tile, spawn_tile), tile[1], tile[0]))
    npc_names = ["Aveline", "Orin", "Mael"]
    npcs = []
    for index, dialogue in enumerate(quest["dialogues"]):
        if not npc_candidates:
            break
        candidate_index = min((index + 1) * len(npc_candidates) // 4, len(npc_candidates) - 1)
        position = npc_candidates.pop(candidate_index)
        npcs.append({
            "id": index,
            "name": npc_names[index],
            "position": list(position),
            "dialogue": dialogue,
            "costume": rng.choice(NPC_COSTUMES),
            "choices": list(NPC_CHOICES[index]),
            "x": float(position[0] * config.TILE_SIZE),
            "y": float(position[1] * config.TILE_SIZE),
            "vx": 0.0,
            "vy": 0.0,
            "facing_left": False,
            "move_timer": rng.uniform(0.5, 2.0),
            "talking_to": None,
        })
    occupied = {tuple(key_position), tuple(door_position)}
    occupied.update(tuple(npc["position"]) for npc in npcs)
    landmark_candidates = [tile for tile in walkable if tile not in occupied]
    rng.shuffle(landmark_candidates)
    landmarks = [
        {"type": "lore_stone", "position": list(landmark_candidates[0])},
        {"type": "passage_rune", "position": list(landmark_candidates[1])},
        {"type": "sealed_chest", "position": list(landmark_candidates[2])},
    ] if len(landmark_candidates) >= 3 else []
    room.set(*key_position, TILE_KEY)
    room.set(*door_position, TILE_DOOR)
    return {
        "enabled": True,
        "quest_id": quest["id"],
        "quest_title": quest["title"],
        "quest_goal": quest["required_npcs"],
        "key_position": list(key_position),
        "door_position": list(door_position),
        "key_collected": False,
        "door_unlocked": False,
        "npcs": npcs,
        "talked_npcs": [],
        "dialogue": None,
        "landmarks": landmarks,
    }


class Host:
    def __init__(self, pseudo="Hôte", seed=None, max_players=4, save_name="Sans nom"):
        self.sel = selectors.DefaultSelector()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setblocking(False)
        self.server_sock.bind(("0.0.0.0", HOST_PORT))
        self.server_sock.listen()
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        self.rng = random.Random(seed)
        shape = generate_room_shape(self.rng, radius=ROOM_RADIUS)
        max_x = max(x for x, y in shape)
        max_y = max(y for x, y in shape)
        ground_positions = [(x + ROOM_MARGIN, y + ROOM_MARGIN) for x, y in shape]
        self.room = autotile_room(
            ground_positions,
            width=max_x + ROOM_MARGIN * 2 + 1,
            height=max_y + ROOM_MARGIN * 2 + 1,
        )

        spawn_tiles = get_spawn_positions(self.room, max_players)
        self.story = _make_story(self.room, spawn_tiles[HOST_SLOT], self.rng)

        self.available_slots = list(range(1, max_players))

        self.clients = {}
        self.next_session_id = 1

        host_x, host_y = spawn_tiles[HOST_SLOT]
        self.players = {
            HOST_SESSION_ID: new_player_state(host_x * config.TILE_SIZE, host_y * config.TILE_SIZE)
        }
        self.pseudos = {
            HOST_SESSION_ID: pseudo
        }
        self._spawn_tiles = spawn_tiles

        self.messages = []

        self.max_players = max_players
        self.save_name = save_name
        self.announcer = Announcer()

    def poll_network(self):
        events = self.sel.select(timeout=0)
        for key, mask in events:
            if key.data is None:
                self._accept_connection()
            else:
                self._read_client(key.data)

    def _accept_connection(self):
        conn, addr = self.server_sock.accept()

        if not self.available_slots:
            print(f"[HOST] Connexion refusée depuis {addr} (partie pleine)")
            try:
                conn.send(encode(make_full_message("Partie pleine")))
            except OSError:
                pass
            conn.close()
            return

        conn.setblocking(False)
        session_id = self.next_session_id
        self.next_session_id += 1
        slot = self.available_slots.pop(0)

        self.clients[session_id] = {
            "conn": conn,
            "recv_buffer": "",
            "keys": {"up": False, "down": False, "left": False, "right": False, "interact": False},
            "slot": slot,
        }
        self.pseudos[session_id] = f"Joueur {session_id}"

        spawn_x, spawn_y = self._spawn_tiles[slot]
        self.players[session_id] = new_player_state(spawn_x * config.TILE_SIZE, spawn_y * config.TILE_SIZE)

        self.sel.register(conn, selectors.EVENT_READ, data=session_id)
        print(f"[HOST] Client {session_id} connecté depuis {addr} (slot {slot})")

        conn.send(encode(make_welcome_message(session_id)))
        conn.send(encode(make_world_message(self.room.to_dict(), self.story)))

    def _read_client(self, session_id):
        client = self.clients[session_id]
        try:
            data = client["conn"].recv(65536)
        except BlockingIOError:
            return
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self._disconnect_client(session_id)
            return

        if not data:
            self._disconnect_client(session_id)
            return

        client["recv_buffer"] += data.decode("utf-8")
        while "\n" in client["recv_buffer"]:
            line, client["recv_buffer"] = client["recv_buffer"].split("\n", 1)
            message = decode((line + "\n").encode("utf-8"))

            if message["type"] == MSG_INPUT:
                client["keys"] = message["keys"]
            elif message["type"] == MSG_JOIN:
                pseudo = message["pseudo"]
                self.pseudos[session_id] = pseudo
                print(f"[HOST] Client {session_id} a choisi le pseudo '{pseudo}'")
                self._broadcast_notice(f"{pseudo} a rejoint la partie.")
            elif message["type"] == MSG_CHAT:
                pseudo = self.pseudos.get(session_id, "???")
                self._broadcast_chat(pseudo, message["text"])

    def _disconnect_client(self, session_id):
        pseudo = self.pseudos.get(session_id, "???")
        print(f"[HOST] Client {session_id} déconnecté")
        self.sel.unregister(self.clients[session_id]["conn"])
        self.available_slots.append(self.clients[session_id]["slot"])
        del self.clients[session_id]
        del self.players[session_id]
        del self.pseudos[session_id]
        self._broadcast_notice(f"{pseudo} a quitté la partie.")

    def _broadcast_chat(self, pseudo, text):
        self.messages.append({"kind": "chat", "pseudo": pseudo, "text": text})
        self._send_to_all(encode(make_chat_broadcast(pseudo, text)))

    def _broadcast_notice(self, text):
        self.messages.append({"kind": "notice", "text": text})
        self._send_to_all(encode(make_notice_message(text)))

    def _send_to_all(self, encoded_message):
        dead_sessions = []
        for session_id, client in self.clients.items():
            try:
                client["conn"].send(encoded_message)
            except BlockingIOError:
                pass
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                dead_sessions.append(session_id)

        for session_id in dead_sessions:
            self._disconnect_client(session_id)

    def send_chat(self, text):
        self._broadcast_chat(self.pseudos[HOST_SESSION_ID], text)

    def update(self, dt, host_keys):
        update_player(self.players[HOST_SESSION_ID], host_keys, dt, self.room)
        for session_id, client in self.clients.items():
            update_player(self.players[session_id], client["keys"], dt, self.room)
        self._update_npcs(dt)
        inputs = {HOST_SESSION_ID: host_keys}
        inputs.update({session_id: client["keys"] for session_id, client in self.clients.items()})
        self._update_story(inputs)

    def _update_npcs(self, dt):
        if not self.story or self.story.get("dialogue"):
            return
        for npc in self.story.get("npcs", []):
            if npc.get("talking_to") is not None:
                continue
            nearest_player = min(
                self.players.values(),
                key=lambda player: (player["x"] - npc["x"]) ** 2 + (player["y"] - npc["y"]) ** 2,
            )
            npc["facing_left"] = nearest_player["x"] < npc["x"]
            npc["move_timer"] -= dt
            if npc["move_timer"] <= 0:
                npc["move_timer"] = self.rng.uniform(0.8, 2.5)
                direction = self.rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)))
                npc["vx"] = direction[0] * 28.0
                npc["vy"] = direction[1] * 28.0

            new_x = npc["x"] + npc["vx"] * dt
            new_y = npc["y"] + npc["vy"] * dt
            if _can_move_to(new_x, npc["y"], self.room):
                npc["x"] = new_x
            else:
                npc["vx"] = 0.0
            if _can_move_to(npc["x"], new_y, self.room):
                npc["y"] = new_y
            else:
                npc["vy"] = 0.0
            if npc["vx"] < 0:
                npc["facing_left"] = True
            elif npc["vx"] > 0:
                npc["facing_left"] = False
            npc["position"] = [
                int(npc["x"] // config.TILE_SIZE),
                int(npc["y"] // config.TILE_SIZE),
            ]

    def _update_story(self, inputs):
        if not self.story:
            return
        dialogue = self.story.get("dialogue")
        if dialogue:
            session_id = dialogue["session_id"]
            choice = inputs.get(session_id, {}).get("choice", 0)
            if choice in range(1, len(dialogue["choices"]) + 1):
                npc_id = dialogue["npc_id"]
                if npc_id not in self.story["talked_npcs"]:
                    self.story["talked_npcs"].append(npc_id)
                for npc in self.story["npcs"]:
                    if npc["id"] == npc_id:
                        npc["talking_to"] = None
                        break
                self.story["dialogue"] = None
                self._broadcast_notice("Votre reponse a ete entendue.")
                if all(npc_id in self.story["talked_npcs"] for npc_id in self.story["quest_goal"]):
                    self.story["door_unlocked"] = True
                    self.room.set(*self.story["door_position"], TILE_GROUND)
                    self._broadcast_notice("Les anciens ont revele le passage. Trouvez la porte.")
            return
        if not self.story["key_collected"]:
            key_x, key_y = self.story["key_position"]
            for player in self.players.values():
                player_tile = (int(player["x"] // config.TILE_SIZE), int(player["y"] // config.TILE_SIZE))
                if player_tile == (key_x, key_y):
                    self.story["key_collected"] = True
                    self._broadcast_notice("Vous avez trouve la cle. Parlez aux anciens du donjon.")
                    return

        if not self.story["door_unlocked"]:
            for session_id, player in self.players.items():
                if not inputs.get(session_id, {}).get("interact"):
                    continue
                player_tile = (int(player["x"] // config.TILE_SIZE), int(player["y"] // config.TILE_SIZE))
                for npc in self.story["npcs"]:
                    npc_position = tuple(npc["position"])
                    if npc["id"] in self.story["talked_npcs"] or _distance(player_tile, npc_position) > 1:
                        continue
                    npc["talking_to"] = session_id
                    nearest_player = self.players[session_id]
                    npc["facing_left"] = nearest_player["x"] < npc["x"]
                    self.story["dialogue"] = {
                        "session_id": session_id,
                        "npc_id": npc["id"],
                        "name": npc["name"],
                        "text": npc["dialogue"],
                        "choices": npc["choices"],
                    }
                    return

        if self.story["door_unlocked"]:
            door_position = tuple(self.story["door_position"])
            for player in self.players.values():
                player_tile = (int(player["x"] // config.TILE_SIZE), int(player["y"] // config.TILE_SIZE))
                if player_tile == door_position:
                    self._advance_story()
                    return

    def _advance_story(self):
        shape = generate_room_shape(self.rng, radius=ROOM_RADIUS)
        max_x = max(x for x, y in shape)
        max_y = max(y for x, y in shape)
        ground_positions = [(x + ROOM_MARGIN, y + ROOM_MARGIN) for x, y in shape]
        self.room = autotile_room(
            ground_positions,
            width=max_x + ROOM_MARGIN * 2 + 1,
            height=max_y + ROOM_MARGIN * 2 + 1,
        )
        self._spawn_tiles = get_spawn_positions(self.room, self.max_players)
        self.story = _make_story(self.room, self._spawn_tiles[HOST_SLOT], self.rng)
        for session_id, player in self.players.items():
            spawn_x, spawn_y = self._spawn_tiles[self.clients[session_id]["slot"]] if session_id != HOST_SESSION_ID else self._spawn_tiles[HOST_SLOT]
            player.update({"x": spawn_x * config.TILE_SIZE, "y": spawn_y * config.TILE_SIZE, "vx": 0.0, "vy": 0.0})
        self._broadcast_notice("Nouvelle salle découverte ! Trouvez la prochaine clé.")
        self._send_to_all(encode(make_world_message(self.room.to_dict(), self.story)))

    def broadcast_state(self):
        if not self.clients:
            return
        self._send_to_all(encode(make_state_message(self.players, self.pseudos, self.story)))

    def tick_announcer(self, dt):
        info = {
            "pseudo": self.pseudos[HOST_SESSION_ID],
            "save_name": self.save_name,
            "current_players": 1 + len(self.clients),
            "max_players": self.max_players,
        }
        self.announcer.tick(dt, info)

    def close(self):
        self.announcer.close()