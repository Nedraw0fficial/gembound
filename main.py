import sys
import math
import pygame
import config
from network.host import Host, HOST_SESSION_ID
from network.client import Client
from network.online_client import OnlineClient
from world.dungeon_renderer import DungeonRenderer
from world.gate_renderer import GateRenderer
from entities.animation import AnimationController
from settings import load_settings, save_settings
from ui.screens import (
    MenuScreen, CreateLobbyScreen, JoinScreen, OptionsScreen,
    SCREEN_MENU, SCREEN_CREATE_LOBBY, SCREEN_JOIN, SCREEN_IN_GAME, SCREEN_OPTIONS,
)
from entities.health_display import HealthDisplay
from ui.health_bar_renderer import HealthBarRenderer



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
    margin = config.CAMERA_ROOM_MARGIN_TILES
    for (min_x, min_y, max_x, max_y) in room_bounds:
        if (min_x - margin) <= tile_x <= (max_x + margin) and (min_y - margin) <= tile_y <= (max_y + margin):
            return (min_x, min_y, max_x, max_y)
    return None


def compute_camera_target(my_pos, room, room_bounds):
    view_w = config.SCREEN_WIDTH // config.SCALE
    view_h = config.SCREEN_HEIGHT // config.SCALE

    camera_x = int(my_pos["x"] - view_w // 2)
    camera_y = int(my_pos["y"] - view_h // 2)
    zoom = 1.0

    tile_x = int(my_pos["x"]) // config.TILE_SIZE
    tile_y = int(my_pos["y"]) // config.TILE_SIZE
    current_room = _find_room_bounds_at(tile_x, tile_y, room_bounds)

    if current_room is not None:
        min_x, min_y, max_x, max_y = current_room
        margin_px = config.CAMERA_ROOM_MARGIN_TILES * config.TILE_SIZE
        room_px_min_x = min_x * config.TILE_SIZE - margin_px
        room_px_min_y = min_y * config.TILE_SIZE - margin_px
        room_px_max_x = (max_x + 1) * config.TILE_SIZE + margin_px
        room_px_max_y = (max_y + 1) * config.TILE_SIZE + margin_px
        room_w = room_px_max_x - room_px_min_x
        room_h = room_px_max_y - room_px_min_y

        if room_w <= view_w and room_h <= view_h:
            zoom = min(view_w / room_w, view_h / room_h)
            zoom = min(zoom, config.CAMERA_MAX_ZOOM)

            effective_view_w = view_w / zoom
            effective_view_h = view_h / zoom

            camera_x = room_px_min_x - (effective_view_w - room_w) / 2
            camera_y = room_px_min_y - (effective_view_h - room_h) / 2
        else:
            camera_x = max(room_px_min_x, min(camera_x, room_px_max_x - view_w))
            camera_y = max(room_px_min_y, min(camera_y, room_px_max_y - view_h))

    else:
        zoom = config.CAMERA_CORRIDOR_ZOOM
        effective_view_w = view_w / zoom
        effective_view_h = view_h / zoom

        camera_x = my_pos["x"] - effective_view_w / 2
        camera_y = my_pos["y"] - effective_view_h / 2

        max_camera_x = max(0, room.width * config.TILE_SIZE - effective_view_w)
        max_camera_y = max(0, room.height * config.TILE_SIZE - effective_view_h)
        camera_x = max(0, min(camera_x, max_camera_x))
        camera_y = max(0, min(camera_y, max_camera_y))

    return camera_x, camera_y, zoom


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
    label_font = pygame.font.Font(config.FONT_PATH, config.PLAYER_LABEL_FONT_SIZE)

    dungeon_renderer = DungeonRenderer()
    gate_renderer = GateRenderer()
    health_bar_renderer = HealthBarRenderer()
    health_displays = {}

    current_screen = SCREEN_MENU
    menu_screen = MenuScreen(font, title_font)
    create_lobby_screen = None
    join_screen = None
    options_screen = None

    network = None
    role = None
    pending_pseudo = None

    chat_active = False
    chat_text = ""

    player_animations = {}

    camera_state = {"x": None, "y": None, "zoom": 1.0}
    elapsed_time = 0.0

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        elapsed_time += dt

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
                    font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_NORMAL)
                    title_font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_TITLE)
                    label_font = pygame.font.Font(config.FONT_PATH, config.PLAYER_LABEL_FONT_SIZE)
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
                    if len(chat_text) < config.MAX_CHAT_LENGTH:
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
                text = font.render(network_error, True, (230, 80, 80))
                hint = font.render("Échap pour revenir au menu", True, (200, 200, 200))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2, config.SCREEN_HEIGHT // 2 - 20))
                screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT // 2 + 20))

            elif room is None or my_id is None or my_id not in network.players:
                text = font.render("Connexion en cours...", True, (255, 255, 255))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2,
                                    config.SCREEN_HEIGHT // 2))

            else:
                my_pos = network.players[my_id]
                target_x, target_y, target_zoom = compute_camera_target(my_pos, room, network.room_bounds)

                if camera_state["x"] is None:
                    camera_state["x"] = float(target_x)
                    camera_state["y"] = float(target_y)
                    camera_state["zoom"] = target_zoom

                pos_t = 1 - math.exp(-config.CAMERA_LERP_SPEED * dt)
                zoom_t = 1 - math.exp(-config.CAMERA_ZOOM_LERP_SPEED * dt)
                camera_state["x"] += (target_x - camera_state["x"]) * pos_t
                camera_state["y"] += (target_y - camera_state["y"]) * pos_t
                camera_state["zoom"] += (target_zoom - camera_state["zoom"]) * zoom_t
                sway_x = math.sin(elapsed_time * config.CAMERA_SWAY_SPEED) * config.CAMERA_SWAY_AMPLITUDE_PX
                sway_y = math.sin(elapsed_time * config.CAMERA_SWAY_SPEED * 0.7 + 1.3) * config.CAMERA_SWAY_AMPLITUDE_PX
                sway_zoom = math.sin(elapsed_time * config.CAMERA_ZOOM_SWAY_SPEED) * config.CAMERA_ZOOM_SWAY_AMPLITUDE

                zoom = max(0.01, camera_state["zoom"] + sway_zoom)
                capture_w = max(1, int(config.SCREEN_WIDTH / zoom))
                capture_h = max(1, int(config.SCREEN_HEIGHT / zoom))
                capture = pygame.Surface((capture_w, capture_h))
                capture.fill((20, 20, 30))

                camera_x = camera_state["x"] + sway_x
                camera_y = camera_state["y"] + sway_y

                dungeon_renderer.render_main_layer(capture, room, camera_x, camera_y)
                gate_renderer.render(capture, network.gates, camera_x, camera_y)
                
                pending_labels = []
                pending_health_bars = []

                sorted_players = sorted(network.players.items(), key=lambda item: item[1]["y"])
                for session_id, pos in sorted_players:
                    if session_id not in player_animations:
                        player_animations[session_id] = AnimationController()
                    anim = player_animations[session_id]

                    if session_id not in health_displays:
                        health_displays[session_id] = HealthDisplay(pos["hp"], pos["max_hp"])
                    health_displays[session_id].update(pos["hp"], pos["max_hp"], dt)

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
                    capture.blit(scaled_frame, (sprite_x, sprite_y))

                    pseudo = network.pseudos.get(session_id, "???")
                    label = label_font.render(pseudo, True, (255, 255, 255))

                    tile_center_x = tile_screen_x + config.DISPLAY_TILE_SIZE / 2
                    screen_label_x = tile_center_x * zoom - label.get_width() / 2
                    screen_label_y = (sprite_y - 8) * zoom
                    pending_labels.append((label, screen_label_x, screen_label_y))
                    if session_id != my_id:
                        health_screen_x = tile_center_x * zoom
                        health_screen_y = screen_label_y
                        pending_health_bars.append((session_id, pos["hp"], health_screen_x, health_screen_y))

                dungeon_renderer.render_overlay_layer(capture, room, camera_x, camera_y)

                scaled_capture = pygame.transform.scale(capture, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                screen.blit(scaled_capture, (0, 0))

                for session_id, hp, hx, hy in pending_health_bars:
                    health_bar_renderer.render_other(screen, health_displays[session_id], hp, hx, hy)

                for label, label_x, label_y in pending_labels:
                    screen.blit(label, (label_x, label_y))

                if my_id in network.players:
                    my_display = health_displays.get(my_id)
                    if my_display is not None:
                        health_bar_renderer.render_own(screen, my_display, network.players[my_id]["hp"])
                
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