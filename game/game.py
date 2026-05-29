import pygame
import random
from game.settings import *
from game.entities import Player, Drone, PlayerBullet, Star


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock  = pygame.font.init() or pygame.time.Clock()
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
        self.score        = 0
        self.frame        = 0
        self.state        = "playing"
        self.stars        = [Star(randomize_y=True) for _ in range(STAR_COUNT)]
        self._last_dir    = ""

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return False
        return True

    def _update(self):
        self.frame += 1
        keys = pygame.key.get_pressed()

        # 玩家移動
        self.player.update(keys)

        # 移動方向輸出
        self._print_direction(keys)

        # 自動射擊
        if self.frame % PLAYER_FIRE_INTERVAL == 0:
            bullet = PlayerBullet(self.player.rect.centerx, self.player.rect.top)
            self.player_bullets.add(bullet)
            self.all_sprites.add(bullet)

        # 生成 Drone（每波 2～3 架並排）
        if self.frame % DRONE_SPAWN_INTERVAL == 0:
            count   = random.randint(2, 3)
            spacing = SCREEN_WIDTH // (count + 1)
            for i in range(count):
                drone = Drone(x=spacing * (i + 1))
                self.enemies.add(drone)
                self.all_sprites.add(drone)

        # 子彈移動
        self.player_bullets.update()

        # 敵人移動
        self.enemies.update()

        # 星空
        for star in self.stars:
            star.update()

        # 碰撞：玩家子彈打中 Drone
        hits = pygame.sprite.groupcollide(
            self.player_bullets, self.enemies, True, True
        )
        self.score += len(hits) * DRONE_SCORE

        # 碰撞：Drone 撞到玩家
        hits = pygame.sprite.spritecollide(
            self.player, self.enemies, True,
            pygame.sprite.collide_mask
        )
        for _ in hits:
            self.player.hp -= 1
            if self.player.hp <= 0:
                self.state = "gameover"
                return

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

    def _print_direction(self, keys):
        dirs = []
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dirs.append("上")
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dirs.append("下")
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dirs.append("左")
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dirs.append("右")
        label = "移動方向：" + "、".join(dirs) if dirs else "靜止"
        if label != self._last_dir:
            print(label)
            self._last_dir = label

    def _draw_hud(self):
        # 分數（左上）
        score_surf = self.font_small.render(f"SCORE  {self.score:07d}", True, GRAY)
        self.screen.blit(score_surf, (10, 10))

        # HP 方塊（右上）
        label = self.font_small.render("HP", True, GRAY)
        self.screen.blit(label, (SCREEN_WIDTH - 10 - self.player.hp * 18 - 30, 10))
        for i in range(self.player.hp):
            x = SCREEN_WIDTH - 10 - (self.player.hp - i) * 18
            pygame.draw.rect(self.screen, CYAN, (x, 10, 14, 14))

    def _gameover_screen(self):
        self.screen.fill(BLACK)
        go_surf    = self.font_large.render("GAME OVER", True, RED)
        sc_surf    = self.font_small.render(f"SCORE  {self.score:07d}", True, GRAY)
        retry_surf = self.font_small.render("Press  R  to retry  /  ESC  to quit", True, WHITE)

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
        return True
