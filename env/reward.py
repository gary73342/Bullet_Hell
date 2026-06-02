import math
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# 甜蜜點：畫面水平中央、垂直 3/4 處
_SWEET_X = SCREEN_WIDTH / 2
_SWEET_Y = SCREEN_HEIGHT * 0.75

# 甜蜜點到最遠角落的距離，用於正規化位置 reward
_MAX_DIST = math.hypot(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.75)

# Reward 數值
REWARD_KILL     =  5.0
REWARD_HIT      = -10.0
REWARD_DEATH    = -50.0
REWARD_STATIC   = -0.5
REWARD_POS_MAX  =  0.02

STATIC_THRESHOLD = 10   # 連續靜止幾步後才扣分


class RewardCalculator:
    def reset(self):
        self._static_steps = 0
        self._last_pos = None

    def calculate(self, player_x, player_y, kills, hit, died):
        """
        每個 env step 呼叫一次（frame skip 結束後）。
        kills : int  — 這個 step 內擊殺的敵人數
        hit   : bool — 這個 step 內玩家是否被擊中
        died  : bool — 這個 step 內玩家是否死亡
        """
        reward = 0.0

        reward += REWARD_KILL * kills

        if hit:
            reward += REWARD_HIT

        if died:
            reward += REWARD_DEATH

        # 靜止懲罰
        pos = (player_x, player_y)
        if self._last_pos is not None and pos == self._last_pos:
            self._static_steps += 1
            if self._static_steps > STATIC_THRESHOLD:
                reward += REWARD_STATIC
        else:
            self._static_steps = 0
        self._last_pos = pos

        # 位置獎勵：越靠近甜蜜點越高
        dist = math.hypot(player_x - _SWEET_X, player_y - _SWEET_Y)
        reward += REWARD_POS_MAX * (1.0 - dist / _MAX_DIST)

        return reward
