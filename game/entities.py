import pygame
import random
from game.settings import *


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self._orig_image  = self._make_surface()
        self._blank_image = pygame.Surface((36, 40), pygame.SRCALPHA)
        self.image = self._orig_image
        self.rect  = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom  = SCREEN_HEIGHT - 30
        self.hp = PLAYER_HP
        self.invincible_frames = 0

    def _make_surface(self):
        surf = pygame.Surface((36, 40), pygame.SRCALPHA)
        # 機身
        pygame.draw.polygon(surf, CYAN, [(18, 0), (0, 40), (36, 40)])
        # 座艙
        pygame.draw.polygon(surf, WHITE, [(18, 6), (10, 28), (26, 28)])
        return surf

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1

        if dx != 0 and dy != 0:
            self.rect.x += int(dx * PLAYER_SPEED * 0.7071)
            self.rect.y += int(dy * PLAYER_SPEED * 0.7071)
        else:
            self.rect.x += dx * PLAYER_SPEED
            self.rect.y += dy * PLAYER_SPEED

        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        if self.invincible_frames > 0:
            self.invincible_frames -= 1
            self.image = self._orig_image if (self.invincible_frames // 5) % 2 == 0 else self._blank_image
        else:
            self.image = self._orig_image


class Drone(pygame.sprite.Sprite):
    def __init__(self, x=None, speed=None):
        super().__init__()
        self.speed  = speed if speed is not None else DRONE_SPEED
        self.image  = self._make_surface()
        self.rect   = self.image.get_rect()
        self.rect.centerx = x if x is not None else random.randint(20, SCREEN_WIDTH - 20)
        self.rect.y = -40
        self.hp     = DRONE_HP
        self._fire_timer = random.randint(0, DRONE_FIRE_INTERVAL)

    def _make_surface(self):
        surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        # 倒三角機身
        pygame.draw.polygon(surf, RED, [(16, 32), (0, 0), (32, 0)])
        # 座艙
        pygame.draw.circle(surf, (255, 140, 100), (16, 10), 6)
        return surf

    def update(self):
        self.rect.y += self.speed
        self._fire_timer += 1
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

    def try_shoot(self, bullet_speed=None):
        """計時到達時回傳新的 EnemyBullet，否則回傳 None。"""
        if self._fire_timer >= DRONE_FIRE_INTERVAL and self.rect.top > 0:
            self._fire_timer = 0
            return EnemyBullet(self.rect.centerx, self.rect.bottom, speed=bullet_speed)
        return None


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=None):
        super().__init__()
        self.speed = speed if speed is not None else ENEMY_BULLET_SPEED
        self.image = pygame.Surface((6, 16), pygame.SRCALPHA)
        self.image.fill(PINK)
        self.rect  = self.image.get_rect(centerx=x, top=y)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()


class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=None):
        super().__init__()
        self.speed = speed if speed is not None else PLAYER_BULLET_SPEED
        self.image = pygame.Surface((7, 20), pygame.SRCALPHA)
        self.image.fill(YELLOW)
        self.rect  = self.image.get_rect(centerx=x, bottom=y)

    def update(self):
        self.rect.y -= self.speed
        if self.rect.bottom < 0:
            self.kill()


class Star:
    def __init__(self, randomize_y=True):
        self.reset(randomize_y)

    def reset(self, randomize_y=False):
        self.x     = random.randint(0, SCREEN_WIDTH)
        self.y     = random.randint(0, SCREEN_HEIGHT) if randomize_y else -2
        self.speed = random.randint(STAR_SPEED_MIN, STAR_SPEED_MAX)
        self.size  = 1 if self.speed == STAR_SPEED_MIN else 2

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.reset()

    def draw(self, surface):
        brightness = 100 + self.speed * 50
        color = (brightness, brightness, brightness)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)
