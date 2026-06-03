import math
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# 甜蜜點：畫面水平中央、垂直 3/4 處
_SWEET_X = SCREEN_WIDTH / 2
_SWEET_Y = SCREEN_HEIGHT * 0.75

# ─── 邊界判定範圍設定 ───
BORDER_MARGIN = 30  # 距離邊界小於 30 像素就算貼邊

# 甜蜜點到最遠角落的距離，用於正規化位置 reward
_MAX_DIST = math.hypot(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.75)

# Reward 數值微調
REWARD_KILL     =  5.0
REWARD_HIT      = -10.0
REWARD_DEATH    = -50.0
REWARD_HEAL     =  2.0     
REWARD_STATIC   = -1.0     # ─── 提高靜止懲罰 (-0.5 -> -1.0) ───
REWARD_BORDER   = -2.0     # ─── 新增：貼邊懲罰（電網） ───
REWARD_POS_MAX  =  0.08    # ─── 提高位置引導 (0.02 -> 0.08) ───

STATIC_THRESHOLD = 8       # ─── 縮短靜止容忍步數 (10 -> 8) ───


class RewardCalculator:
    def reset(self):
        self._static_steps = 0

    def calculate(self, player_x, player_y, kills, hit, died, dx, dy, healed):
        """
        每個 env step 呼叫一次（frame skip 結束後）。
        kills : int  — 這個 step 內擊殺的敵人數
        hit   : bool — 這個 step 內玩家是否被擊中
        died  : bool — 這個 step 內玩家是否死亡
        dx/dy : int  — 這個 step 的移動方向（0 表示未輸入）
        """
        reward = 0.0

        reward += REWARD_KILL * kills

        if hit:
            reward += REWARD_HIT

        if died:
            reward += REWARD_DEATH

        # 補血獎勵
        if healed:
            reward += REWARD_HEAL

        # 靜止懲罰：只在真正選擇不動時累積（貼牆但有移動輸入不算）
        if dx == 0 and dy == 0:
            self._static_steps += 1
            if self._static_steps > STATIC_THRESHOLD:
                reward += REWARD_STATIC * (1.0 + (self._static_steps - STATIC_THRESHOLD) * 0.1)
        else:
            self._static_steps = 0

        # 3. ─── 新增：貼邊懲罰（邊界電網） ───
        is_at_left   = player_x < BORDER_MARGIN
        is_at_right  = player_x > (SCREEN_WIDTH - BORDER_MARGIN)
        is_at_top    = player_y < BORDER_MARGIN
        is_at_bottom = player_y > (SCREEN_HEIGHT - BORDER_MARGIN)
        if is_at_left or is_at_right or is_at_top or is_at_bottom:
            reward += REWARD_BORDER
            # 如果貼邊的同時還「靜止不動」，給予追加懲罰
            if dx == 0 and dy == 0:
                reward += REWARD_BORDER * 1.5

        # 位置獎勵：越靠近甜蜜點越高
        dist = math.hypot(player_x - _SWEET_X, player_y - _SWEET_Y)
        reward += REWARD_POS_MAX * (1.0 - dist / _MAX_DIST)

        return reward
