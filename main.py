import sys
import pygame
import config
from network.host import Host, HOST_SESSION_ID
from network.client import Client
from world.dungeon_renderer import DungeonRenderer
from entities.animation import AnimationController
from settings import load_settings, save_settings
from ui.screens import OptionsScreen, SCREEN_OPTIONS
from ui.screens import MenuScreen, CreateLobbyScreen, JoinScreen, SCREEN_MENU, SCREEN_CREATE_LOBBY, SCREEN_JOIN, SCREEN_IN_GAME
from network.online_client import OnlineClient


PLAYER_COLORS = [
    (220, 80, 80),
    (80, 160, 220),
    (80, 220, 120),
    (220, 200, 80),
]

NOTICE_COLOR = (230, 200, 60)
CHAT_COLOR = (255, 255, 255)
MAX_VISIBLE_MESSAGES = 8


def get_my_session_id(network, role):
    if role == "host":
        return HOST_SESSION_ID
    return network.session_id


def get_keys_pressed(settings):
    keys = pygame.key.get_pressed()
    return {
        "up": any(keys[k] for k in settings.keybinds["up"]),
        "down": any(keys[k] for k in settings.keybinds["down"]),
        "left": any(keys[k] for k in settings.keybinds["left"]),
        "right": any(keys[k] for k in settings.keybinds["right"]),
    }


def format_message(msg):
    if msg["kind"] == "notice":
        return msg["text"], NOTICE_COLOR
    return f"[{msg['pseudo']}] {msg['text']}", CHAT_COLOR


def _find_room_bounds_at(tile_x, tile_y, room_bounds):
    for (min_x, min_y, max_x, max_y) in room_bounds:
        if min_x <= tile_x <= max_x and min_y <= tile_y <= max_y:
            return (min_x, min_y, max_x, max_y)
    return None


def compute_camera(my_pos, room, room_bounds):
    view_w = config.SCREEN_WIDTH // config.SCALE
    view_h = config.SCREEN_HEIGHT // config.SCALE

    camera_x = int(my_pos["x"] - view_w // 2)
    camera_y = int(my_pos["y"] - view_h // 2)

    tile_x = int(my_pos["x"]) // config.TILE_SIZE
    tile_y = int(my_pos["y"]) // config.TILE_SIZE
    current_room = _find_room_bounds_at(tile_x, tile_y, room_bounds)

    if current_room is not None:
        min_x, min_y, max_x, max_y = current_room
        room_px_min_x = min_x * config.TILE_SIZE
        room_px_min_y = min_y * config.TILE_SIZE
        room_px_max_x = (max_x + 1) * config.TILE_SIZE
        room_px_max_y = (max_y + 1) * config.TILE_SIZE
        room_w = room_px_max_x - room_px_min_x
        room_h = room_px_max_y - room_px_min_y

        if room_w <= view_w:
            camera_x = room_px_min_x - (view_w - room_w) // 2
        else:
            camera_x = max(room_px_min_x, min(camera_x, room_px_max_x - view_w))

        if room_h <= view_h:
            camera_y = room_px_min_y - (view_h - room_h) // 2
        else:
            camera_y = max(room_px_min_y, min(camera_y, room_px_max_y - view_h))
    else:
        max_camera_x = max(0, room.width * config.TILE_SIZE - view_w)
        max_camera_y = max(0, room.height * config.TILE_SIZE - view_h)
        camera_x = max(0, min(camera_x, max_camera_x))
        camera_y = max(0, min(camera_y, max_camera_y))

    return camera_x, camera_y

def _apply_display_mode(settings):
    if settings.fullscreen:
        info = pygame.display.Info()
        width, height = info.current_w, info.current_h
        flags = pygame.FULLSCREEN
    else:
        width, height = settings.resolution
        flags = 0

    screen = pygame.display.set_mode((width, height), flags)
    config.apply_resolution(width, height)
    return screen



def main():
    pygame.init()

    settings = load_settings()
    screen = _apply_display_mode(settings)

    pygame.display.set_caption(config.GAME_TITLE)
    clock = pygame.time.Clock()

    font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_NORMAL)
    title_font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_TITLE)
    label_font = pygame.font.Font(config.FONT_PATH, 18)

    dungeon_renderer = DungeonRenderer()

    current_screen = SCREEN_MENU
    menu_screen = MenuScreen(font, title_font)
    create_lobby_screen = None
    join_screen = None

    network = None
    role = None
    pending_pseudo = None

    chat_active = False
    chat_text = ""

    player_animations = {}

    options_screen = None
    
    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if current_screen == SCREEN_JOIN and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                join_screen.close()
                current_screen = SCREEN_MENU
                continue

            if current_screen == SCREEN_MENU:
                result = menu_screen.handle_event(event)
                if result:
                    mode, pending_pseudo = result
                    if mode == "create":
                        create_lobby_screen = CreateLobbyScreen(font)
                        current_screen = SCREEN_CREATE_LOBBY
                    elif mode == "join":
                        join_screen = JoinScreen(font, pending_pseudo)
                        current_screen = SCREEN_JOIN
                    elif mode == "options":
                        options_screen = OptionsScreen(font, settings)
                        current_screen = SCREEN_OPTIONS

            elif current_screen == SCREEN_CREATE_LOBBY:
                result = create_lobby_screen.handle_event(event)
                if result:
                    if result["is_lan"]:
                        network = Host(
                            pseudo=pending_pseudo,
                            seed=result["seed"],
                            max_players=result["max_players"],
                            save_name=result["name"],
                        )
                        role = "host"
                    else:
                        network = OnlineClient(pending_pseudo)
                        network.create_lobby(
                            result["name"], result["seed"],
                            result["max_players"], result["password"],
                        )
                        role = "online_client"
                    current_screen = SCREEN_IN_GAME

            elif current_screen == SCREEN_JOIN:
                result = join_screen.handle_event(event)
                if result:
                    if result[0] == "lan":
                        _, ip = result
                        join_screen.close()
                        try:
                            network = Client(ip, pseudo=pending_pseudo)
                        except ConnectionError as e:
                            print(f"[NETWORK] {e}")
                            continue
                        role = "client"
                    else:
                        _, lobby_id, password = result
                        network = join_screen.directory_client
                        network.join_lobby(lobby_id, password)
                        join_screen.close_lan_listener()
                        role = "online_client"
                    current_screen = SCREEN_IN_GAME

            elif current_screen == SCREEN_OPTIONS:
                result = options_screen.handle_event(event)
                if result == "resolution_changed":
                    screen = _apply_display_mode(settings)
                    options_screen = OptionsScreen(font, settings)
                elif result == "back":
                        save_settings(settings)
                        menu_screen = MenuScreen(font, title_font)
                        current_screen = SCREEN_MENU

            elif current_screen == SCREEN_IN_GAME:
                has_error = getattr(network, "rejected_reason", None) or getattr(network, "lobby_error", None)
                if has_error and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    network = None
                    role = None
                    current_screen = SCREEN_MENU
                    continue
                if event.type == pygame.KEYDOWN:
                    if not chat_active:
                        if event.key == pygame.K_RETURN:
                            chat_active = True
                            chat_text = ""
                    else:
                        if event.key == pygame.K_RETURN:
                            if chat_text.strip():
                                network.send_chat(chat_text.strip())
                            chat_active = False
                            chat_text = ""
                        elif event.key == pygame.K_ESCAPE:
                            chat_active = False
                            chat_text = ""
                        elif event.key == pygame.K_BACKSPACE:
                            chat_text = chat_text[:-1]
                elif event.type == pygame.TEXTINPUT and chat_active:
                    chat_text += event.text

        screen.fill((20, 20, 30))

        if current_screen == SCREEN_MENU:
            menu_screen.update(mouse_pos)
            menu_screen.draw(screen)

        elif current_screen == SCREEN_CREATE_LOBBY:
            create_lobby_screen.update(mouse_pos)
            create_lobby_screen.draw(screen)

        elif current_screen == SCREEN_JOIN:
            join_screen.update(mouse_pos)
            join_screen.draw(screen)

        elif current_screen == SCREEN_OPTIONS:
            options_screen.update(mouse_pos)
            options_screen.draw(screen)

        elif current_screen == SCREEN_IN_GAME:
            my_keys = get_keys_pressed(settings) if not chat_active else {"up": False, "down": False, "left": False, "right": False}

            if role == "host":
                network.tick_announcer(dt)
                network.poll_network()
                network.update(dt, my_keys)
                network.broadcast_state()
            else:
                network.send_input(my_keys)
                network.poll_network()

            my_id = get_my_session_id(network, role)
            room = network.room

            network_error = None
            if role in ("client", "online_client"):
                network_error = getattr(network, "rejected_reason", None) or getattr(network, "lobby_error", None)
            if network_error:
                text = font.render(network.rejected_reason, True, (230, 80, 80))
                hint = font.render("Échap pour revenir au menu", True, (200, 200, 200))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2, config.SCREEN_HEIGHT // 2 - 20))
                screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT // 2 + 20))
            elif room is None or my_id is None or my_id not in network.players:
                text = font.render("Connexion en cours...", True, (255, 255, 255))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2,
                                    config.SCREEN_HEIGHT // 2))
            else:
                my_pos = network.players[my_id]
                camera_x, camera_y = compute_camera(my_pos, room, network.room_bounds)

                dungeon_renderer.render_main_layer(screen, room, camera_x, camera_y)
                pending_labels = []
                
                sorted_players = sorted(network.players.items(), key=lambda item: item[1]["y"])
                for session_id, pos in sorted_players:
                    if session_id not in player_animations:
                        player_animations[session_id] = AnimationController()
                    anim = player_animations[session_id]

                    speed = (pos["vx"] ** 2 + pos["vy"] ** 2) ** 0.5
                    if speed > 5:
                        anim.set_animation("walking")
                        if pos["vx"] < -1:
                            anim.set_facing(True)
                        elif pos["vx"] > 1:
                            anim.set_facing(False)
                    else:
                        anim.set_animation("idle")
                    anim.update(dt)

                    color = PLAYER_COLORS[session_id % len(PLAYER_COLORS)]
                    frame = anim.get_current_frame(color)

                    tile_screen_x = pos["x"] * config.SCALE - camera_x * config.SCALE
                    tile_screen_y = pos["y"] * config.SCALE - camera_y * config.SCALE

                    sprite_w = int(config.PLAYER_SPRITE_WIDTH * config.SCALE * config.PLAYER_SIZE_MULTIPLIER)
                    sprite_h = int(config.PLAYER_SPRITE_HEIGHT * config.SCALE * config.PLAYER_SIZE_MULTIPLIER)
                    foot_row_scaled = config.PLAYER_FOOT_ROW * config.SCALE

                    sprite_x = tile_screen_x + (config.DISPLAY_TILE_SIZE - sprite_w) // 2
                    sprite_y = tile_screen_y + config.DISPLAY_TILE_SIZE - foot_row_scaled

                    scaled_frame = pygame.transform.scale(frame, (sprite_w, sprite_h))
                    screen.blit(scaled_frame, (sprite_x, sprite_y))

                    pseudo = network.pseudos.get(session_id, "???")
                    label = label_font.render(pseudo, True, (255, 255, 255))
                    label_x = tile_screen_x + config.DISPLAY_TILE_SIZE // 2 - label.get_width() // 2
                    pending_labels.append((label, label_x, sprite_y - 8))

                dungeon_renderer.render_overlay_layer(screen, room, camera_x, camera_y)

                for label, label_x, label_y in pending_labels:
                    screen.blit(label, (label_x, label_y))

                visible_messages = network.messages[-MAX_VISIBLE_MESSAGES:]
                base_y = config.SCREEN_HEIGHT - 30 - len(visible_messages) * 22
                for i, msg in enumerate(visible_messages):
                    text_str, color = format_message(msg)
                    rendered = font.render(text_str, True, color)
                    screen.blit(rendered, (10, base_y + i * 22))

                if chat_active:
                    input_rect_y = config.SCREEN_HEIGHT - 30
                    pygame.draw.rect(screen, (0, 0, 0), (10, input_rect_y - 4, 400, 26))
                    input_text = font.render("> " + chat_text, True, (255, 255, 255))
                    screen.blit(input_text, (14, input_rect_y))

        pygame.display.flip()

    if network is not None and role == "host":
        network.close()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()