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
REWARD_HIT_BASE = -4.0   # 前期基礎值，每升 5 級再 -2
REWARD_DEATH    = -50.0
REWARD_HEAL     =  2.0     
REWARD_STATIC   = -1.0     # ─── 提高靜止懲罰 (-0.5 -> -1.0) ───
REWARD_BORDER   = -2.0     # ─── 新增：貼邊懲罰（電網） ───
REWARD_POS_MAX  =  0.08    # ─── 提高位置引導 (0.02 -> 0.08) ───

STATIC_THRESHOLD = 8       # ─── 縮短靜止容忍步數 (10 -> 8) ───


# ─── 新增：動作平滑與生存里程碑參數 ───
REWARD_SMOOTH_PENALTY = -0.1   # 鬼畜抖動的懲罰值（微量扣分）
REWARD_TIME_MILESTONE = 15.0   # 每活過一個里程碑給的大獎勵
MILESTONE_FRAMES      = 150    # 里程碑門檻（150 env steps × frame_skip 4 = 600 遊戲幀 = 10秒）

class RewardCalculator:
    def reset(self):
        self._static_steps = 0

    def calculate(self, player_x, player_y, kills, hit, died, dx, dy, healed, prev_action, curr_action, current_frame, player_level=0):
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
            reward += REWARD_HIT_BASE - 2.0 * (player_level // 5)

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

        """
        擴充參數：
        prev_action   : int - 上一步採取的動作編號
        curr_action   : int - 這一步採取的動作編號
        current_frame : int - 當前這一局（episode）總共執行了幾幀
        """
        # 2. ─── 新增：動作平滑懲罰（Action Smoothness） ───
        # 假設你的動作定義：0:不動, 1:左, 2:右, 3:上, 4:下（請根據你實際的 action space 對調）
        # 如果上一步向左(1)這步向右(2)，或者上一步向右(2)這步向左(1)，代表在鬼畜抖動
        if prev_action is not None:
            is_shaking_y = (prev_action == 1 and curr_action == 2) or (prev_action == 2 and curr_action == 1)
            is_shaking_x = (prev_action == 3 and curr_action == 4) or (prev_action == 4 and curr_action == 3)

            if is_shaking_x or is_shaking_y:
                reward += REWARD_SMOOTH_PENALTY

        # 3. ─── 新增：生存時間里程碑獎勵 ───
        # 剛好達到 10秒、20秒、30秒 的瞬間（整除時），給予一筆大獎勵
        if current_frame > 0 and current_frame % MILESTONE_FRAMES == 0:
            reward += REWARD_TIME_MILESTONE

        return reward
