import math
from game.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_HP as MAX_HP

# ─── 邊界判定範圍設定 ───
BORDER_MARGIN = 30  # 距離邊界小於 30 像素就算貼邊

# Reward 數值微調
REWARD_KILL     =  5.0
REWARD_HIT_BASE = -4.0   # 前期基礎值，每升 5 級再 -2
REWARD_DEATH    = -50.0
REWARD_HEAL     =  2.5   # 基底值，實際依 HP 縮放（最高 2 倍）
REWARD_STATIC   = -1.0
REWARD_BORDER   = -2.0

# ─── Potential-Based Repulsive Field 參數 ───
# 改用指數衰減 K·exp(-d/σ)，消除硬截斷造成的 Φ 不連續性
# K 值依「積分等能量」原則換算：K_exp = K_coulomb·ln(71)/σ，中距離數值相近
DANGER_BULLET_K  = 6.0     # 子彈排斥場強度（原 35.0 等效換算）
DANGER_ENEMY_K   = 2.6     # 敵機排斥場強度（原 15.0 等效換算）
SIGMA_BULLET     = 25.0    # 子彈指數衰減長度常數（px）
SIGMA_ENEMY      = 25.0    # 敵機指數衰減長度常數（px）
GAMMA            = 0.999   # 與 PPO 的折扣因子一致

# ─── X 軸對齊獎勵參數 ───
X_ALIGN_REWARD    = 0.06   # 完全對齊時每步的獎勵上限
X_ALIGN_THRESHOLD = 48     # X 距離小於此值才給獎勵（px）

STATIC_THRESHOLD = 8       # ─── 縮短靜止容忍步數 (10 -> 8) ───


REWARD_SURVIVE =  0.1   # 每步存活的連續獎勵

class RewardCalculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self._static_steps = 0
        self._prev_phi = None

    def _compute_phi(self, player_x, player_y, bullet_positions, enemy_positions):
        phi = 0.0
        for bx, by in bullet_positions:
            d = math.hypot(player_x - bx, player_y - by)
            phi -= DANGER_BULLET_K * math.exp(-d / SIGMA_BULLET)
        for ex, ey in enemy_positions:
            d = math.hypot(player_x - ex, player_y - ey)
            phi -= DANGER_ENEMY_K * math.exp(-d / SIGMA_ENEMY)
        return phi

    def calculate(self, player_x, player_y, kills, hit, died, dx, dy, healed, bullet_positions, enemy_positions, player_level=0, player_hp=5, is_invincible=False):
        
        reward = 0.0

        reward += REWARD_KILL * kills

        if hit:
            reward += REWARD_HIT_BASE - 2.0 * (player_level // 5)

        if died:
            reward += REWARD_DEATH

        # 補血獎勵（依缺血量縮放，最高 2 倍）
        if healed:
            scale = min(2.0, MAX_HP / (player_hp + 1))
            reward += REWARD_HEAL * scale

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

        # Potential-Based Repulsive Field：shaping = γΦ(s') − Φ(s)
        phi_curr = self._compute_phi(player_x, player_y, bullet_positions, enemy_positions)
        if is_invincible:
            self._prev_phi = None
        elif self._prev_phi is not None:
            reward += GAMMA * phi_curr - self._prev_phi
            self._prev_phi = phi_curr
        else:
            self._prev_phi = phi_curr

        reward += REWARD_SURVIVE

        # X 軸對齊獎勵：對齊在玩家上方的敵機
        enemies_above = [(ex, ey) for ex, ey in enemy_positions if ey < player_y]
        if enemies_above:
            min_x_dist = min(abs(player_x - ex) for ex, ey in enemies_above)
            if min_x_dist < X_ALIGN_THRESHOLD:
                reward += X_ALIGN_REWARD * (1.0 - min_x_dist / X_ALIGN_THRESHOLD)

        return reward
