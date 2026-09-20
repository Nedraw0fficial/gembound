import config


class HealthDisplay:
    def __init__(self, hp, max_hp):
        self.displayed_hp = hp
        self.max_hp = max_hp

    def update(self, real_hp, real_max_hp, dt):
        self.max_hp = real_max_hp

        if real_hp > self.displayed_hp:
            # heal
            self.displayed_hp = real_hp
        elif real_hp < self.displayed_hp:
            # dmg
            factor = 1 - pow(2.71828, -config.HEALTH_DRAIN_LERP_SPEED * dt)
            self.displayed_hp += (real_hp - self.displayed_hp) * factor
            if self.displayed_hp - real_hp < 0.5:
                self.displayed_hp = real_hp

    def get_segments(self, real_hp):
        filled = real_hp
        white = max(0.0, self.displayed_hp - real_hp)
        return filled, white
