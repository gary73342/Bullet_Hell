import pygame
import random
from game.settings import *


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = self._make_surface()
        self.rect  = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom   = SCREEN_HEIGHT - 30
        self.hp = PLAYER_HP

    def _make_surface(self):
        surf = pygame.Surface((36, 40), pygame.SRCALPHA)
        # 機身
        pygame.draw.polygon(surf, CYAN, [(18, 0), (0, 40), (36, 40)])
        # 座艙
        pygame.draw.polygon(surf, WHITE, [(18, 6), (10, 28), (26, 28)])
        return surf

    def update(self, keys):
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += PLAYER_SPEED
        if keys[pygame.K_UP]   or keys[pygame.K_w]:
            self.rect.y -= PLAYER_SPEED
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            self.rect.y += PLAYER_SPEED

        # 邊界限制
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))


class Drone(pygame.sprite.Sprite):
    def __init__(self, x=None):
        super().__init__()
        self.image  = self._make_surface()
        self.rect   = self.image.get_rect()
        self.rect.centerx = x if x is not None else random.randint(20, SCREEN_WIDTH - 20)
        self.rect.y = -40
        self.hp     = DRONE_HP

    def _make_surface(self):
        surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        # 倒三角機身
        pygame.draw.polygon(surf, RED, [(16, 32), (0, 0), (32, 0)])
        # 座艙
        pygame.draw.circle(surf, (255, 140, 100), (16, 10), 6)
        return surf

    def update(self):
        # 直線向下移動
        self.rect.y += DRONE_SPEED

        # 飛出畫面下方就移除
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()


class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((7, 20), pygame.SRCALPHA)
        self.image.fill(YELLOW)
        self.rect  = self.image.get_rect(centerx=x, bottom=y)

    def update(self):
        self.rect.y -= PLAYER_BULLET_SPEED
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
