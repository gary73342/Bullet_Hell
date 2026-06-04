import os
import sys
import math
import numpy as np
from collections import deque

import pygame
from gymnasium import Env, spaces

# 把 game_ext/ 和 game_ext/game 都加進 path
_EXT_ROOT = os.path.join(os.path.dirname(__file__), '..', 'game_ext')
_GAME_DIR  = os.path.join(_EXT_ROOT, 'game')
sys.path.insert(0, os.path.abspath(_EXT_ROOT))
sys.path.insert(0, os.path.abspath(_GAME_DIR))

EXT_W = 512
EXT_H = 512

OBS_W   = 84
OBS_H   = 84
N_STACK = 4
N_CH    = 3

MAX_BULLETS  = 20
MAX_MONSTERS = 10
# state vector: [x, y] + bullets*2 + monsters*2
VEC_DIM = 2 + MAX_BULLETS * 2 + MAX_MONSTERS * 2

# (dx, dy) 正負對應方向：右/下為正
ACTION_MAP = {
    0: ( 0,  0),  # 不動
    1: (-1,  0),  # 左
    2: ( 1,  0),  # 右
    3: ( 0, -1),  # 上
    4: ( 0,  1),  # 下
    5: (-1, -1),  # 左上
    6: ( 1, -1),  # 右上
    7: (-1,  1),  # 左下
    8: ( 1,  1),  # 右下
}

# ── Reward 參數（與 env/reward.py 對齊） ──────────────────────────────────
REWARD_DEATH   = -50.0
REWARD_STATIC  = -1.0
REWARD_BORDER  = -2.0
REWARD_SURVIVE =  0.1
BORDER_MARGIN  = 30

DANGER_BULLET_K = 6.0
DANGER_ENEMY_K  = 2.6
SIGMA_BULLET    = 25.0
SIGMA_ENEMY     = 25.0
GAMMA           = 0.999

STATIC_THRESHOLD = 8


class ExtBulletHellEnv(Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode

        if render_mode != "human":
            os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
            os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

        import main as ext_main
        self._Main = ext_main.Main
        self._game = ext_main.Main()
        self._game.ms_per_round = 0  # 移除人類遊玩用的幀率限制

        self.action_space = spaces.Discrete(len(ACTION_MAP))  # 9 個動作
        self.observation_space = spaces.Dict({
            "pixels": spaces.Box(
                low=0, high=255,
                shape=(N_STACK * N_CH, OBS_H, OBS_W),
                dtype=np.uint8,
            ),
            "state": spaces.Box(
                low=0.0, high=1.0,
                shape=(VEC_DIM,),
                dtype=np.float32,
            ),
        })

        self._frame_stack = deque(maxlen=N_STACK)
        self._static_steps = 0
        self._prev_phi     = None

    # ── 公開介面 ──────────────────────────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._soft_reset()
        self._static_steps = 0
        self._prev_phi     = None

        frame = self._capture_frame()
        for _ in range(N_STACK):
            self._frame_stack.append(frame)

        return self._get_obs(), {}

    def step(self, action):
        dx, dy = ACTION_MAP[int(action)]
        hb = self._game.hitbox
        hb.xMove = dx * hb.x_dist
        hb.yMove = dy * hb.y_dist

        # 傳 2（K_x）只觸發射擊，不注入方向鍵，移動由上面直接設定
        _reward, _img, death = self._game.MainLoop(2)

        self._frame_stack.append(self._capture_frame())

        px = hb.rect.centerx
        py = hb.rect.centery

        bullet_positions  = [(b.rect.centerx, b.rect.centery)
                             for b in self._game.monster_bullet_group]
        monster_positions = [(m.rect.centerx, m.rect.centery)
                             for m in self._game.monster_group]

        reward = self._compute_reward(px, py, death, dx, dy, bullet_positions, monster_positions)

        if self.render_mode == "human":
            self.render()

        info = {"score": self._game.score}
        return self._get_obs(), reward, death, False, info

    def render(self):
        pygame.display.flip()

    def close(self):
        pygame.quit()

    # ── 內部方法 ──────────────────────────────────────────────────────────

    def _soft_reset(self):
        g = self._game
        g.monster_bullet_group.empty()
        g.player_bullet_group.empty()
        g.monster_group.empty()
        g.shield_group.empty()
        g.wall_vertical_group.empty()
        g.wall_horizontal_group.empty()
        g.level = 0
        g.levelInit()
        g.variableInit()              # 內部會呼叫 spawnPlayer()
        g.ms_per_round = 0            # variableInit 會重設為 30，強制覆蓋
        g.initGame(g.playerList[2][1])  # 覆蓋成 ormrinn，再呼叫 spawnPlayer + startGame

    def _capture_frame(self):
        surface = pygame.display.get_surface()
        if surface is None:
            return np.zeros((N_CH, OBS_H, OBS_W), dtype=np.uint8)
        arr = pygame.surfarray.array3d(surface)       # (512, 512, 3)
        small = pygame.transform.scale(
            pygame.surfarray.make_surface(arr), (OBS_W, OBS_H)
        )
        frame = pygame.surfarray.array3d(small)       # (OBS_W, OBS_H, 3)
        return frame.transpose(2, 1, 0).astype(np.uint8)  # (3, OBS_H, OBS_W)

    def _stack_obs(self):
        return np.concatenate(list(self._frame_stack), axis=0)  # (12, OBS_H, OBS_W)

    def _get_structured_obs(self):
        px = self._game.hitbox.rect.centerx
        py = self._game.hitbox.rect.centery

        vec = [px / EXT_W, py / EXT_H]

        def dist2(pos):
            return (pos[0] - px) ** 2 + (pos[1] - py) ** 2

        bullets = sorted(
            [(b.rect.centerx, b.rect.centery) for b in self._game.monster_bullet_group],
            key=dist2
        )[:MAX_BULLETS]
        for bx, by in bullets:
            vec += [bx / EXT_W, by / EXT_H]
        vec += [0.0, 0.0] * (MAX_BULLETS - len(bullets))

        monsters = sorted(
            [(m.rect.centerx, m.rect.centery) for m in self._game.monster_group],
            key=dist2
        )[:MAX_MONSTERS]
        for mx, my in monsters:
            vec += [mx / EXT_W, my / EXT_H]
        vec += [0.0, 0.0] * (MAX_MONSTERS - len(monsters))

        return np.array(vec, dtype=np.float32)

    def _get_obs(self):
        return {
            "pixels": self._stack_obs(),
            "state":  self._get_structured_obs(),
        }

    def _compute_reward(self, px, py, died, dx, dy, bullet_positions, monster_positions):
        reward = 0.0

        if died:
            reward += REWARD_DEATH
            return reward

        reward += REWARD_SURVIVE

        # 靜止懲罰
        if dx == 0 and dy == 0:
            self._static_steps += 1
            if self._static_steps > STATIC_THRESHOLD:
                reward += REWARD_STATIC * (1.0 + (self._static_steps - STATIC_THRESHOLD) * 0.1)
        else:
            self._static_steps = 0

        # 貼邊懲罰
        at_border = (
            px < BORDER_MARGIN or px > (EXT_W - BORDER_MARGIN) or
            py < BORDER_MARGIN or py > (EXT_H - BORDER_MARGIN)
        )
        if at_border:
            reward += REWARD_BORDER
            if dx == 0 and dy == 0:
                reward += REWARD_BORDER * 1.5

        # Potential-Based 排斥場
        phi_curr = self._compute_phi(px, py, bullet_positions, monster_positions)
        if self._prev_phi is not None:
            reward += GAMMA * phi_curr - self._prev_phi
        self._prev_phi = phi_curr

        return reward

    def _compute_phi(self, px, py, bullet_positions, monster_positions):
        phi = 0.0
        for bx, by in bullet_positions:
            d = math.hypot(px - bx, py - by)
            phi -= DANGER_BULLET_K * math.exp(-d / SIGMA_BULLET)
        for mx, my in monster_positions:
            d = math.hypot(px - mx, py - my)
            phi -= DANGER_ENEMY_K * math.exp(-d / SIGMA_ENEMY)
        return phi
