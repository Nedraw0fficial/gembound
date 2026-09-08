import sys
import pygame
import config
from network.host import Host
from network.client import Client
from world.renderer import Renderer


def choose_mode():
    print("=== GEMBOUND ===")
    choice = input("Héberger (h) ou rejoindre (j) ? ").strip().lower()
    if choice == "h":
        return Host(), "host"
    else:
        ip = input("IP de l'hôte (ex: 192.168.1.42) : ").strip()
        return Client(ip), "client"


def get_keys_pressed():
    keys = pygame.key.get_pressed()
    return {
        "up": keys[pygame.K_UP] or keys[pygame.K_z],
        "down": keys[pygame.K_DOWN] or keys[pygame.K_s],
        "left": keys[pygame.K_LEFT] or keys[pygame.K_q],
        "right": keys[pygame.K_RIGHT] or keys[pygame.K_d],
    }


def get_tilemap(network, role):
    """L'hôte a toujours sa tilemap. Le client peut ne pas l'avoir reçue encore."""
    if role == "host":
        return network.tilemap
    return network.tilemap  #peut être NONE au tout début côté client


def main():
    network, role = choose_mode()

    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption(f"{config.GAME_TITLE} — {role}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    renderer = Renderer()

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        my_keys = get_keys_pressed()

        if role == "host":
            network.poll_network()
            network.update(dt, my_keys)
            network.broadcast_state()
        else:
            network.send_input(my_keys)
            network.poll_network()

        tilemap = get_tilemap(network, role)

        screen.fill((20, 20, 30))

        if tilemap is None:
            # client pas encore reçu le monde : écran d'attente
            text = font.render("En attente du monde...", True, (255, 255, 255))
            screen.blit(text, (config.SCREEN_WIDTH // 2 - text.get_width() // 2,
                                config.SCREEN_HEIGHT // 2))
        else:
            my_pos = network.players[role]
            camera_x = int(my_pos["x"] - config.SCREEN_WIDTH // (2 * config.SCALE))
            camera_y = int(my_pos["y"] - config.SCREEN_HEIGHT // (2 * config.SCALE))
            camera_x = max(0, min(camera_x, config.WORLD_WIDTH * config.TILE_SIZE - config.SCREEN_WIDTH // config.SCALE))
            camera_y = max(0, min(camera_y, config.WORLD_HEIGHT * config.TILE_SIZE - config.SCREEN_HEIGHT // config.SCALE))

            renderer.render(screen, tilemap, camera_x, camera_y)

            colors = {"host": (220, 80, 80), "client": (80, 160, 220)}
            for name, pos in network.players.items():
                screen_x = pos["x"] * config.SCALE - camera_x * config.SCALE
                screen_y = pos["y"] * config.SCALE - camera_y * config.SCALE
                pygame.draw.rect(
                    screen, colors[name],
                    (screen_x, screen_y, config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE)
                )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()