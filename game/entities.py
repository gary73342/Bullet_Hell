import pygame
import random
import math
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
        self.hitbox = pygame.Rect(0, 0, 32, 8)
        self.hitbox.center = self.rect.center

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
        self._move(dx, dy)

    def _move(self, dx, dy):
        if dx != 0 and dy != 0:
            self.rect.x += int(dx * PLAYER_SPEED * 0.7071)
            self.rect.y += int(dy * PLAYER_SPEED * 0.7071)
        else:
            self.rect.x += dx * PLAYER_SPEED
            self.rect.y += dy * PLAYER_SPEED

        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # ─── 新增：讓 hitbox 永遠跟隨戰機的中心點，大小縮到 8x8 ───
        self.hitbox = pygame.Rect(0, 0, 32, 8)
        self.hitbox.center = self.rect.center

        if self.invincible_frames > 0:
            self.invincible_frames -= 1
            self.image = self._orig_image if (self.invincible_frames // 5) % 2 == 0 else self._blank_image
        else:
            self.image = self._orig_image


class Drone(pygame.sprite.Sprite):
    def __init__(self, x=None, speed=None, fire_interval=None, hp=None):
        super().__init__()
        self.speed         = speed if speed is not None else DRONE_SPEED
        self.fire_interval = fire_interval if fire_interval is not None else DRONE_FIRE_INTERVAL
        self.image  = self._make_surface()
        self.rect   = self.image.get_rect()
        self.rect.centerx = x if x is not None else random.randint(20, SCREEN_WIDTH - 20)
        self.rect.y = -40
        self.hp     = hp if hp is not None else DRONE_HP
        self._fire_timer = random.randint(0, self.fire_interval)

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
        if self._fire_timer >= self.fire_interval and self.rect.top > 0:
            self._fire_timer = 0
            return EnemyBullet(self.rect.centerx, self.rect.bottom, speed=bullet_speed)
        return None


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=None):
        super().__init__()
        self.speed = speed if speed is not None else ENEMY_BULLET_SPEED
        self.image = pygame.Surface((18, 24), pygame.SRCALPHA)
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


class HealItem(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.speed = HEAL_ITEM_SPEED
        self.image = self._make_surface()
        self.rect  = self.image.get_rect()
        # 隨機在畫面水平範圍內生成，留 20px 邊距避免貼邊
        self.rect.centerx = random.randint(20, SCREEN_WIDTH - 20)
        self.rect.y = -32

    def _make_surface(self):
        # 建立 24x24 帶 Alpha 通道的畫布
        surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        # 繪製綠色十字：先畫橫矩形，再畫直矩形
        pygame.draw.rect(surf, GREEN, (0, 8, 24, 8))
        pygame.draw.rect(surf, GREEN, (8, 0, 8, 24))
        return surf

    def update(self):
        self.rect.y += self.speed
        # 超出畫面底部則自動刪除
        if self.rect.top > SCREEN_HEIGHT + 10:
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


class ExplosionParticle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 隨機散射角度 (0 ~ 2*pi) 與速度 (2 ~ 5)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        # 初始隨機大小 (3 ~ 6 像素)
        self.size = random.randint(3, 6)
        self.lifetime = random.randint(15, 25)  # 存活幀數
        
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.image.fill(ORANGE)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        # 依速度移動
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        
        # 生命週期遞減
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        else:
            # 隨時間縮小粒子
            new_size = max(1, int(self.size * (self.lifetime / 20)))
            if new_size != self.size:
                self.size = new_size
                self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                self.image.fill(ORANGE)
                # 保持中心點不變
                cx, cy = self.rect.center
                self.rect = self.image.get_rect(center=(cx, cy))