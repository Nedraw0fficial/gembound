import sys
import pygame
import config
from network.host import Host, HOST_SESSION_ID
from network.client import Client
from world.renderer import Renderer
from ui.screens import MenuScreen, HostSetupScreen, JoinScreen, SCREEN_MENU, SCREEN_HOST_SETUP, SCREEN_JOIN, SCREEN_IN_GAME

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


def get_keys_pressed():
    keys = pygame.key.get_pressed()
    return {
        "up": keys[pygame.K_UP] or keys[pygame.K_z],
        "down": keys[pygame.K_DOWN] or keys[pygame.K_s],
        "left": keys[pygame.K_LEFT] or keys[pygame.K_q],
        "right": keys[pygame.K_RIGHT] or keys[pygame.K_d],
    }


def format_message(msg):
    if msg["kind"] == "notice":
        return msg["text"], NOTICE_COLOR
    return f"[{msg['pseudo']}] {msg['text']}", CHAT_COLOR


def main():
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption(config.GAME_TITLE)
    clock = pygame.time.Clock()

    font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_NORMAL)
    title_font = pygame.font.Font(config.FONT_PATH, config.FONT_SIZE_TITLE)
    label_font = pygame.font.Font(config.FONT_PATH, 18)

    renderer = Renderer()

    current_screen = SCREEN_MENU
    menu_screen = MenuScreen(font, title_font)
    host_setup_screen = None
    join_screen = None

    network = None
    role = None
    pending_pseudo = None

    chat_active = False
    chat_text = ""

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
                    if mode == "host":
                        host_setup_screen = HostSetupScreen(font)
                        current_screen = SCREEN_HOST_SETUP
                    else:
                        join_screen = JoinScreen(font)
                        current_screen = SCREEN_JOIN

            elif current_screen == SCREEN_HOST_SETUP:
                result = host_setup_screen.handle_event(event)
                if result:
                    network = Host(
                        pseudo=pending_pseudo,
                        seed=result["seed"],
                        max_players=result["max_players"],
                        save_name=result["save_name"],
                    )
                    role = "host"
                    current_screen = SCREEN_IN_GAME

            elif current_screen == SCREEN_JOIN:
                ip = join_screen.handle_event(event)
                if ip:
                    join_screen.close()
                    network = Client(ip, pseudo=pending_pseudo)
                    role = "client"
                    current_screen = SCREEN_IN_GAME

            elif current_screen == SCREEN_IN_GAME:
                if getattr(network, "rejected_reason", None) and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
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

        elif current_screen == SCREEN_HOST_SETUP:
            host_setup_screen.update(mouse_pos)
            host_setup_screen.draw(screen)

        elif current_screen == SCREEN_JOIN:
            join_screen.update(mouse_pos)
            join_screen.draw(screen)

        elif current_screen == SCREEN_IN_GAME:
            my_keys = get_keys_pressed() if not chat_active else {"up": False, "down": False, "left": False, "right": False}

            if role == "host":
                network.tick_announcer(dt)
                network.poll_network()
                network.update(dt, my_keys)
                network.broadcast_state()
            else:
                network.send_input(my_keys)
                network.poll_network()

            my_id = get_my_session_id(network, role)
            tilemap = network.tilemap

            if role == "client" and getattr(network, "rejected_reason", None):
                text = font.render(network.rejected_reason, True, (230, 80, 80))
                hint = font.render("Échap pour revenir au menu", True, (200, 200, 200))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2, config.SCREEN_HEIGHT // 2 - 20))
                screen.blit(hint, (config.SCREEN_WIDTH // 2 - hint.get_width() // 2, config.SCREEN_HEIGHT // 2 + 20))
            elif tilemap is None or my_id is None or my_id not in network.players:
                text = font.render("Connexion en cours...", True, (255, 255, 255))
                screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2,
                                    config.SCREEN_HEIGHT // 2))
            else:
                my_pos = network.players[my_id]
                camera_x = int(my_pos["x"] - config.SCREEN_WIDTH // (2 * config.SCALE))
                camera_y = int(my_pos["y"] - config.SCREEN_HEIGHT // (2 * config.SCALE))
                camera_x = max(0, min(camera_x, config.WORLD_WIDTH * config.TILE_SIZE - config.SCREEN_WIDTH // config.SCALE))
                camera_y = max(0, min(camera_y, config.WORLD_HEIGHT * config.TILE_SIZE - config.SCREEN_HEIGHT // config.SCALE))

                renderer.render(screen, tilemap, camera_x, camera_y)

                for session_id, pos in network.players.items():
                    color = PLAYER_COLORS[session_id % len(PLAYER_COLORS)]
                    screen_x = pos["x"] * config.SCALE - camera_x * config.SCALE
                    screen_y = pos["y"] * config.SCALE - camera_y * config.SCALE
                    pygame.draw.rect(
                        screen, color,
                        (screen_x, screen_y, config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE)
                    )

                    pseudo = network.pseudos.get(session_id, "???")
                    label = label_font.render(pseudo, True, (255, 255, 255))
                    label_x = screen_x + config.DISPLAY_TILE_SIZE // 2 - label.get_width() // 2
                    screen.blit(label, (label_x, screen_y - 20))

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