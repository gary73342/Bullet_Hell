import os
import pygame
import random
import math
from game.settings import *
from game.entities import Player, Drone, PlayerBullet, EnemyBullet, Star, HealItem,ExplosionParticle

# 編隊模板：每個數字是 X 軸比例（0~1），最少 2 隻
_FORMATIONS = [
    [0.2, 0.5, 0.8],
    [0.3, 0.5, 0.7],
    [0.35, 0.65],
    [0.1, 0.5, 0.9],
    [0.2, 0.4, 0.6, 0.8],
    [0.15, 0.85],
    [0.25, 0.75],
    [0.1, 0.3, 0.7, 0.9],
    [0.4, 0.6],
    [0.2, 0.35, 0.65, 0.8],
    [0.15, 0.4, 0.6, 0.85],
    [0.3, 0.7],
    # 大波次（5～6 隻）
    [0.1, 0.25, 0.5, 0.75, 0.9],
    [0.15, 0.3, 0.5, 0.7, 0.85],
]


class Game:
    def __init__(self, headless=False):
        if headless:
            _saved_driver = os.environ.get("SDL_VIDEODRIVER")
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        if headless:
            if _saved_driver is None:
                os.environ.pop("SDL_VIDEODRIVER", None)
            else:
                os.environ["SDL_VIDEODRIVER"] = _saved_driver
        if headless:
            self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption(TITLE)
        pygame.font.init()
        self.clock  = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("monospace", 36, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 20)

    # ── 公開介面 ──────────────────────────────────────────
    def run(self):
        self._reset()
        while True:
            if self.state == "playing":
                if not self._handle_events():
                    return
                self._update()
                self._draw()
            elif self.state == "gameover":
                if not self._gameover_screen():
                    return
                self._reset()
            self.clock.tick(FPS)

    # ── 內部方法 ──────────────────────────────────────────
    def _reset(self):
        self.player       = Player()
        self.all_sprites  = pygame.sprite.Group(self.player)
        self.enemies      = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets  = pygame.sprite.Group()
        self.heal_items     = pygame.sprite.Group()
        self.explosions     = pygame.sprite.Group()
        self._next_spawn    = 0
        self._fire_timer    = 0
        self.score              = 0
        self.frame              = 0
        self.level              = 0
        self.player_level       = 0
        self.player_kills       = 0
        self.player_fire_interval  = PLAYER_FIRE_INTERVAL
        self.player_bullet_speed   = PLAYER_BULLET_SPEED
        self.state              = "playing"
        self.stars        = [Star(randomize_y=True) for _ in range(STAR_COUNT)]

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return False
        return True

    def _add_kills(self, count):
        self.player_kills += count
        if self.player_level >= PLAYER_MAX_LEVEL:
            while self.player_kills >= PLAYER_KILLS_PER_LEVEL:
                self.player_kills -= PLAYER_KILLS_PER_LEVEL
                self.player.hp = min(PLAYER_HP, self.player.hp + PLAYER_HP // 2)
            return
        while self.player_kills >= PLAYER_KILLS_PER_LEVEL and self.player_level < PLAYER_MAX_LEVEL:
            self.player_kills -= PLAYER_KILLS_PER_LEVEL
            self.player_level += 1
            self.player.hp = min(PLAYER_HP, self.player.hp + PLAYER_HP // 2)
            self.player_fire_interval = max(6, self.player_fire_interval - 0.1)
            self.player_bullet_speed += 1
            self.player.speed = PLAYER_SPEED + self.player_level // 5

    def _level_params(self):
        lv = self.level
        drone_speed    = min(9.0, DRONE_SPEED + lv * 0.25)
        bullet_speed   = min(11.0, ENEMY_BULLET_SPEED + lv * 0.25)
        spawn_interval = max(42, DRONE_SPAWN_INTERVAL - lv * 2)
        fire_interval  = max(DRONE_FIRE_INTERVAL_MIN, DRONE_FIRE_INTERVAL - lv * 6)
        drone_hp       = min(3, 1 + lv // 8)
        return drone_speed, bullet_speed, spawn_interval, fire_interval, drone_hp

    def _update(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1
        kill_count, hit, died, healed, _ = self._tick(dx, dy)

    def _tick(self, dx, dy):
        pygame.event.pump()
        self.frame += 1
        self.level = self.frame // (10 * FPS)

        self.player._move(dx, dy)

        # 自動射擊
        self._fire_timer += 1
        if self._fire_timer >= self.player_fire_interval:
            self._fire_timer = 0
        if self._fire_timer == 0:
            positions = (
                [self.player.rect.centerx - 8, self.player.rect.centerx + 8]
                if self.player_level >= 10
                else [self.player.rect.centerx]
            )
            for x in positions:
                bullet = PlayerBullet(x, self.player.rect.top, speed=self.player_bullet_speed)
                self.player_bullets.add(bullet)
                self.all_sprites.add(bullet)

        drone_speed, bullet_speed, spawn_interval, fire_interval, drone_hp = self._level_params()

        # Formation 模式：指數分布決定下波時機，隨機挑編隊模板
        if self.frame >= self._next_spawn:
            formation = random.choice(_FORMATIONS)
            for ratio in formation:
                jitter = random.uniform(-0.05, 0.05)
                x = int(SCREEN_WIDTH * max(0.05, min(0.95, ratio + jitter)))
                drone = Drone(x=x, speed=drone_speed, fire_interval=fire_interval, hp=drone_hp)
                self.enemies.add(drone)
                self.all_sprites.add(drone)
            self._next_spawn = self.frame + int(random.uniform(spawn_interval * 0.5, spawn_interval * 1.5))


        # 等級 10 前每 5 秒，10 級後每 3 秒，必定生成
        heal_interval = 180 if self.level >= 10 else HEAL_DROP_INTERVAL
        if self.frame % heal_interval == 0:
            heal_item = HealItem()
            self.heal_items.add(heal_item)
            self.all_sprites.add(heal_item)

        # 子彈移動
        self.player_bullets.update()
        self.enemy_bullets.update()

        # 敵人移動 + 射擊
        self.enemies.update()
        self.heal_items.update() # 新增：更新補血包位置
        # ─── 補上這行：讓爆炸粒子開始計算散射、縮小與消失 ───
        self.explosions.update()

        for drone in self.enemies:
            bullet = drone.try_shoot(bullet_speed=bullet_speed)
            if bullet:
                self.enemy_bullets.add(bullet)
                self.all_sprites.add(bullet)

        # 星空
        for star in self.stars:
            star.update()

        # 碰撞：玩家子彈打中 Drone（子彈消滅，敵機扣血）
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, False)
        kill_count = 0

        hit_drones = {}
        for bullet, enemy_list in hits.items():
            for drone in enemy_list:
                hit_drones[drone] = hit_drones.get(drone, 0) + 1

        for drone, damage in hit_drones.items():
            drone.hp -= damage
            if drone.hp <= 0:
                drone.kill()
                kill_count += 1
                self.score += DRONE_SCORE
                for _ in range(12):
                    p = ExplosionParticle(drone.rect.centerx, drone.rect.centery)
                    self.explosions.add(p)
                    self.all_sprites.add(p)

        if kill_count > 0:
            self._add_kills(kill_count)

        hit = False
        died = False
        healed = False  # 新增：紀錄本步是否吃到補血

        heal_hits = [item for item in self.heal_items if self.player.rect.colliderect(item.rect)]
        pre_heal_hp = None
        if heal_hits:
            for item in heal_hits:
                item.kill()
            old_hp = self.player.hp
            pre_heal_hp = old_hp
            self.player.hp = min(PLAYER_HP, self.player.hp + HEAL_ITEM_HP_RESTORE)
            healed = self.player.hp > old_hp

        # 碰撞：Drone 撞到玩家
        hits = pygame.sprite.spritecollide(
            self.player, self.enemies, True, pygame.sprite.collide_mask
        )
        if hits and self.player.invincible_frames == 0:
            self.player.hp -= 1
            self.player.invincible_frames = PLAYER_INVINCIBLE_FRAMES
            hit = True
            if self.player.hp <= 0:
                self.state = "gameover"
                died = True
                return kill_count, hit, died, healed, pre_heal_hp

        # 碰撞：敵人子彈打中玩家的核心 Hitbox
        # 原本是：pygame.sprite.spritecollide(self.player, self.enemy_bullets, True)
        # ─── 修改為自訂碰撞區域 ───
        hit_bullets = [b for b in self.enemy_bullets if self.player.hitbox.colliderect(b.rect)]
        
        if hit_bullets and self.player.invincible_frames == 0:
            for b in hit_bullets:
                b.kill()
            
            self.player.hp -= 1
            self.player.invincible_frames = PLAYER_INVINCIBLE_FRAMES
            hit = True
            if self.player.hp <= 0:
                self.state = "gameover"
                died = True

        return kill_count, hit, died, healed, pre_heal_hp

    def _draw(self):
        self.screen.fill(BLACK)

        # 星空
        for star in self.stars:
            star.draw(self.screen)

        # Sprites
        self.all_sprites.draw(self.screen)

        # HUD
        self._draw_hud()

        pygame.display.flip()

    def _draw_hud(self):
        # 分數（頂端置中，大字）
        score_surf = self.font_large.render(f"{self.score}", True, WHITE)
        self.screen.blit(score_surf, score_surf.get_rect(centerx=SCREEN_WIDTH // 2, top=8))

        # 左上：敵方難度
        stage_surf = self.font_small.render(f"STAGE  {self.level}", True, GRAY)
        self.screen.blit(stage_surf, (10, 10))

        # 右上：HP 方塊
        hp_label = self.font_small.render("HP", True, GRAY)
        self.screen.blit(hp_label, (SCREEN_WIDTH - 10 - self.player.hp * 18 - 30, 10))
        for i in range(self.player.hp):
            x = SCREEN_WIDTH - 10 - (self.player.hp - i) * 18
            pygame.draw.rect(self.screen, CYAN, (x, 10, 14, 14))

        # 右上：玩家等級與進度條（HP 下方）
        plv_surf = self.font_small.render(f"P-LV  {self.player_level}", True, CYAN)
        self.screen.blit(plv_surf, plv_surf.get_rect(right=SCREEN_WIDTH - 10, top=30))
        bar_total = 80
        if self.player_level < PLAYER_MAX_LEVEL:
            filled = int(bar_total * self.player_kills / PLAYER_KILLS_PER_LEVEL)
        else:
            filled = int(bar_total * self.player_kills / PLAYER_KILLS_PER_LEVEL)
        pygame.draw.rect(self.screen, GRAY, (SCREEN_WIDTH - 10 - bar_total, 50, bar_total, 6))
        pygame.draw.rect(self.screen, CYAN, (SCREEN_WIDTH - 10 - bar_total, 50, filled,    6))

    def _update_ai(self, dx, dy):
        return self._tick(dx, dy)

    def _draw_objects(self, surface):
        surface.fill(BLACK)
        # ─── 移除了 for star in self.stars: star.draw(surface) ───
        # 這樣 Agent 隱藏畫布就不會看到無意義的星星雜訊，背景保持全黑
        self.all_sprites.draw(surface) # 畫布只保留戰機、敵機、子彈、補血包

    def _gameover_screen(self):
        go_surf    = self.font_large.render("GAME OVER", True, RED)
        sc_surf    = self.font_small.render(f"SCORE  {self.score}", True, GRAY)
        retry_surf = self.font_small.render("Press  R  to retry  /  ESC  to quit", True, WHITE)

        while True:
            self.screen.fill(BLACK)
            self.screen.blit(go_surf,    go_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50)))
            self.screen.blit(sc_surf,    sc_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
            self.screen.blit(retry_surf, retry_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50)))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return False
                    if event.key == pygame.K_r:
                        return True
            self.clock.tick(FPS)
