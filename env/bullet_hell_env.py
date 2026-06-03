import numpy as np
import pygame
from collections import deque
from gymnasium import Env, spaces

from game.game import Game
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from env.reward import RewardCalculator

OBS_W      = 84    # 縮放後寬度
OBS_H      = 112   # 縮放後高度
N_STACK    = 4     # 堆疊幀數
N_CH       = 3     # RGB 通道數
FRAME_SKIP = 4     # 每次 step 執行幾幀遊戲邏輯

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

        # 觀測空間：4幀 × RGB，PyTorch channel-first (C, H, W)
        self.observation_space = spaces.Box(
            low=0, high=255,
            shape=(N_STACK * N_CH, OBS_H, OBS_W),  # (12, 112, 84)
            dtype=np.uint8,
        )

        self._frame_stack = deque(maxlen=N_STACK)
        self._reward_calc = RewardCalculator()
        self._game        = Game(headless=(render_mode != "human"))
        self._offscreen   = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # ─── 修正：在實例化時宣告這兩個紀錄變數 ───
        self.current_frame = 0
        self.prev_action = None

    # ── 公開介面 ──────────────────────────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._game._reset()
        self._reward_calc.reset()

        # ─── 修正：每局重置時，計數器與歷史動作歸零 ───
        self.current_frame = 0
        self.prev_action = None

        frame = self._capture_frame()
        for _ in range(N_STACK):
            self._frame_stack.append(frame)
        return self._stack_obs(), {}

    def step(self, action):
        # 把 action 轉為整數
        act_idx = int(action)
        dx, dy = ACTION_MAP[act_idx]
        kills, hit, died, healed = 0, False, False, False

        for _ in range(FRAME_SKIP):
            k, h, d, hl = self._game_step(dx, dy)
            kills     += k
            hit        = hit or h
            died       = died or d
            healed     = healed or hl  # 只要 frame skip 期間有一次吃到就演算法認定吃到
            if died:
                break

        self._frame_stack.append(self._capture_frame())

        # ─── 修正：將 prev_action, curr_action (即 act_idx) 與 current_frame 傳入計算機 ───
        reward = self._reward_calc.calculate(
            player_x=self._game.player.rect.centerx,
            player_y=self._game.player.rect.centery,
            kills=kills, hit=hit, died=died,
            dx=dx, dy=dy, healed=healed,
            prev_action=self.prev_action,
            curr_action=act_idx,
            current_frame=self.current_frame
        )

        # ─── 修正：在計算完 Reward 後，把這一步的動作存下來，變成「下一步的上一步」 ───
        self.prev_action = act_idx

        if self.render_mode == "human":
            self.render()

        info = {
            "score":        self._game.score,
            "hp":           self._game.player.hp,
            "level":        self._game.level,
            "player_level": self._game.player_level,
        }

        return self._stack_obs(), reward, died, False, info

    def render(self):
        self._game._draw()

    def close(self):
        pygame.quit()

    # ── 內部方法 ──────────────────────────────────────────────────────────

    def _capture_frame(self):
        self._game._draw_objects(self._offscreen)
        small = pygame.transform.scale(self._offscreen, (OBS_W, OBS_H))
        frame = pygame.surfarray.array3d(small)        # (OBS_W, OBS_H, 3)
        return frame.transpose(2, 1, 0).astype(np.uint8)  # (3, OBS_H, OBS_W)

    def _stack_obs(self):
        return np.concatenate(list(self._frame_stack), axis=0)  # (12, OBS_H, OBS_W)

    def _game_step(self, dx, dy):
        return self._game._update_ai(dx, dy)
