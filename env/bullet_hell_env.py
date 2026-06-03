import numpy as np
import pygame
from collections import deque
from gymnasium import Env, spaces

from game.game import Game
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_HP as MAX_HP
from env.reward import RewardCalculator

OBS_W      = 84    # 縮放後寬度
OBS_H      = 112   # 縮放後高度
N_STACK    = 4     # 堆疊幀數
N_CH       = 3     # RGB 通道數
FRAME_SKIP = 4     # 每次 step 執行幾幀遊戲邏輯

MAX_BULLETS = 20
MAX_ENEMIES = 10
MAX_HEALS   = 3
VEC_DIM     = 3 + MAX_BULLETS * 2 + MAX_ENEMIES * 2 + MAX_HEALS * 2  # 69

# 動作編號 → (dx, dy)
ACTION_MAP = {
    0: ( 0,  0),  # 不動
    1: ( 0, -1),  # 上
    2: ( 0, +1),  # 下
    3: (-1,  0),  # 左
    4: (+1,  0),  # 右
    5: (-1, -1),  # 左上
    6: (+1, -1),  # 右上
    7: (-1, +1),  # 左下
    8: (+1, +1),  # 右下
}


class BulletHellEnv(Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode

        # 動作空間：9 個離散動作（含對角）
        self.action_space = spaces.Discrete(len(ACTION_MAP))

        self.observation_space = spaces.Dict({
            "pixels": spaces.Box(
                low=0, high=255,
                shape=(N_STACK * N_CH, OBS_H, OBS_W),  # (12, 112, 84)
                dtype=np.uint8,
            ),
            "state": spaces.Box(
                low=0.0, high=1.0,
                shape=(VEC_DIM,),
                dtype=np.float32,
            ),
        })

        self._frame_stack = deque(maxlen=N_STACK)
        self._reward_calc = RewardCalculator()
        self._game        = Game(headless=(render_mode != "human"))
        self._offscreen   = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # ── 公開介面 ──────────────────────────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._game._reset()
        self._reward_calc.reset()

        frame = self._capture_frame()
        for _ in range(N_STACK):
            self._frame_stack.append(frame)
        return self._get_obs(), {}

    def step(self, action):
        # 把 action 轉為整數
        act_idx = int(action)
        dx, dy = ACTION_MAP[act_idx]
        kills, hit, died, healed = 0, False, False, False
        pre_heal_hp = self._game.player.hp

        for _ in range(FRAME_SKIP):
            k, h, d, hl, phhp = self._game_step(dx, dy)
            kills     += k
            hit        = hit or h
            died       = died or d
            healed     = healed or hl
            if phhp is not None:
                pre_heal_hp = phhp
            if died:
                break

        self._frame_stack.append(self._capture_frame())

        bullet_positions = [(b.rect.centerx, b.rect.centery) for b in self._game.enemy_bullets]
        enemy_positions  = [(e.rect.centerx, e.rect.centery) for e in self._game.enemies]

        reward = self._reward_calc.calculate(
            player_x=self._game.player.rect.centerx,
            player_y=self._game.player.rect.centery,
            kills=kills, hit=hit, died=died,
            dx=dx, dy=dy, healed=healed,
            bullet_positions=bullet_positions,
            enemy_positions=enemy_positions,
            player_level=self._game.player_level,
            player_hp=pre_heal_hp,
            is_invincible=self._game.player.invincible_frames > 0,
        )

        if self.render_mode == "human":
            self.render()

        info = {
            "score":        self._game.score,
            "hp":           self._game.player.hp,
            "level":        self._game.level,
            "player_level": self._game.player_level,
        }

        return self._get_obs(), reward, died, False, info

    def render(self):
        self._game._draw()

    def close(self):
        pygame.quit()

    # ── 內部方法 ──────────────────────────────────────────────────────────

    def _get_obs(self):
        return {
            "pixels": self._stack_obs(),
            "state":  self._get_structured_obs(),
        }

    def _get_structured_obs(self):
        g = self._game
        player_pos = (g.player.rect.centerx, g.player.rect.centery)

        vec = [
            g.player.rect.centerx / SCREEN_WIDTH,
            g.player.rect.centery / SCREEN_HEIGHT,
            g.player.hp / MAX_HP,
        ]

        def dist2(pos):
            return (pos[0] - player_pos[0])**2 + (pos[1] - player_pos[1])**2

        bullets = sorted(
            [(b.rect.centerx, b.rect.centery) for b in g.enemy_bullets], key=dist2
        )[:MAX_BULLETS]
        for bx, by in bullets:
            vec += [bx / SCREEN_WIDTH, by / SCREEN_HEIGHT]
        vec += [0.0, 0.0] * (MAX_BULLETS - len(bullets))

        enemies = sorted(
            [(e.rect.centerx, e.rect.centery) for e in g.enemies], key=dist2
        )[:MAX_ENEMIES]
        for ex, ey in enemies:
            vec += [ex / SCREEN_WIDTH, ey / SCREEN_HEIGHT]
        vec += [0.0, 0.0] * (MAX_ENEMIES - len(enemies))

        heals = sorted(
            [(h.rect.centerx, h.rect.centery) for h in g.heal_items], key=dist2
        )[:MAX_HEALS]
        for hx, hy in heals:
            vec += [hx / SCREEN_WIDTH, hy / SCREEN_HEIGHT]
        vec += [0.0, 0.0] * (MAX_HEALS - len(heals))

        return np.array(vec, dtype=np.float32)

    def _capture_frame(self):
        self._game._draw_objects(self._offscreen)
        small = pygame.transform.scale(self._offscreen, (OBS_W, OBS_H))
        frame = pygame.surfarray.array3d(small)        # (OBS_W, OBS_H, 3)
        return frame.transpose(2, 1, 0).astype(np.uint8)  # (3, OBS_H, OBS_W)

    def _stack_obs(self):
        return np.concatenate(list(self._frame_stack), axis=0)  # (12, OBS_H, OBS_W)

    def _game_step(self, dx, dy):
        return self._game._update_ai(dx, dy)
