import sys
import pygame
import config
from network.host import Host
from network.client import Client


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


def main():
    network, role = choose_mode()

    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption(f"{config.GAME_TITLE} — {role}")
    clock = pygame.time.Clock()

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

        screen.fill((20, 20, 30))

        colors = {"host": (220, 80, 80), "client": (80, 160, 220)}
        for name, pos in network.players.items():
            pygame.draw.rect(
                screen, colors[name],
                (pos["x"], pos["y"], config.DISPLAY_TILE_SIZE, config.DISPLAY_TILE_SIZE)
            )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()