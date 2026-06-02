# Bullet Hell DRL 專題規劃文件

> 近代人工智慧期末專題 — 國立中央大學數學系
> 成員：112201040、112201527

---

## 一、專題概述

使用 Python 開發一款彈幕射擊（Bullet Hell）遊戲，包裝成 Gymnasium 環境，透過 CNN + PPO 演算法訓練一個能自主遊玩的 DRL agent，目標是達到或超越人類玩家水準。

---

## 二、技術架構

### 整體流程

```
Python 遊戲 (Pygame)
       ↓ 包裝
Gym 環境 (Gymnasium)
       ↓ 觀測 / 動作 / 獎勵
CNN + PPO 訓練
       ↓ 儲存參數
Agent 展示
```

### 各層說明

#### 1. 遊戲層（Pygame）

自行開發彈幕射擊遊戲，包含：

- 玩家機體：可上下左右移動，自動射擊
- 敵人系統：四種敵人類型
  - Drone（直衝型）：直線衝向玩家，無子彈
  - Shooter（固定砲台）：停在固定位置，持續發射扇形 / 瞄準彈
  - Sniper（狙擊型）：蓄力後發射高速直線彈，蓄力時顯示警示線
  - Swarm（群體型）：多隻小型敵人陣形出現，同時發射
- Boss 系統：多階段 Boss，血量降低時切換攻擊模式
- 子彈模式：直線、扇形、瞄準彈、螺旋彈、環形爆散、分裂彈、波浪彈（待定）
- 關卡系統：三個關卡，難度逐步遞增

##### 第一關（已實作）

**類別結構**

| 類別 | 說明 |
|------|------|
| `Player` | 玩家戰機，WASD / 方向鍵移動，對角速度 normalize，自動射擊，受擊後無敵幀閃爍 |
| `Drone` | 敵機，直線向下移動，獨立計時器每 90 幀發射直線子彈（初始隨機偏移避免齊射） |
| `PlayerBullet` | 我方子彈，向上直線移動，速度隨玩家等級動態變化 |
| `EnemyBullet` | 敵方子彈（粉紅），向下直線移動，速度隨 STAGE 動態變化 |
| `Star` | 星空背景粒子，隨機速度與亮度，飛出畫面後重置 |

**系統**

- **STAGE 系統**（敵方難度）：每 8 秒（480 幀）提升一級，動態調整四項數值：
  - 敵機速度：`DRONE_SPEED + stage × 0.5`
  - 敵機子彈速度：`ENEMY_BULLET_SPEED + stage × 0.5`
  - 生成間隔：`max(40, 90 − stage × 8)` 幀
  - 每波數量：`min(5, 2 + stage // 2)` 架

- **P-LV 系統**（玩家升級）：每 15 擊殺升一級，最高 6 級，升級效果：
  - 回復 5 HP（上限 10）
  - 射擊間隔 ÷ 1.2（下限 2 幀）
  - 子彈速度 +2
  - Level 4 起解鎖雙行子彈（左右各偏移 8px）

- **碰撞偵測**：我方子彈 vs 敵機、敵機本體 vs 玩家、敵方子彈 vs 玩家（受擊後觸發無敵幀）

- **HUD**：頂部分數置中（大字）、左上 STAGE、右上 HP 方塊 + P-LV + 升級進度條

---

#### 2. Gym 包裝層（Gymnasium）

實作三個核心方法：

```python
def reset(self)  → 回傳初始觀測值
def step(self, action)  → 執行動作，回傳 (obs, reward, done, info)
def render(self)  → 訓練時關閉，展示時開啟
```

**觀測空間**

| 版本 | 觀測方式 | Shape | Policy |
|------|----------|-------|--------|
| Baseline | 向量（玩家座標、子彈相對位置等） | (23,) | MlpPolicy |
| CNN n=1 | 彩色截圖 | (3, 112, 84) | CnnPolicy |
| CNN n=4 ✓ | 彩色截圖 × frame stacking | (12, 112, 84) | CnnPolicy |

**確定規格：**
- 解析度：**84×112**（保留 3:4 比例，由 480×640 縮小）
- 色彩：**RGB**（顏色有語義，不使用灰階）
- Frame Stacking：**4 幀**，shape `(12, 112, 84)`，PyTorch channel-first
- Frame Skip：**4**（每 4 幀做一次決策，等效 15 次/秒）
- HUD 處理：使用 **offscreen surface**，觀測畫面不含 HUD；HP、分數等透過 `info` dict 傳遞

**動作空間**

```
Discrete(9)：
0: 不動
1: 上      2: 下
3: 左      4: 右
5: 左上    6: 右上
7: 左下    8: 右下
射擊設為自動，不佔動作維度
```

**Reward Function**

```python
reward += +5.0  * kills              # 擊殺普通敵人
reward += -10.0 * hit                # 被子彈擊中
reward += -50.0 * died               # 死亡（終局）
reward += -0.5  * (static > 10步)    # 連續靜止懲罰，避免躲角落
reward += +0.02 * (1 - dist / max_dist)  # 靠近甜蜜點獎勵
```

**甜蜜點**：x = 畫面中央（240px），y = 畫面 3/4 處（480px）

**移除項目**：每幀存活 reward（消極求生）、Boss 擊殺 reward（Boss 尚未實作）

**參考論文**：DeepMind DQN (2013, 2015)，論文使用純分數作為 reward + Reward Clipping (±1)。本專題針對自訂遊戲加入輔助 reward，Clipping 留待訓練後視穩定性決定是否加入。

**實作**：`env/reward.py` — `RewardCalculator.calculate(player_x, player_y, kills, hit, died)`

#### 3. 訓練層

**演算法：** PPO（Proximal Policy Optimization）

**套件：** SB3（第一階段）→ 視時間決定是否換成手刻 PyTorch PPO

**資料流**

```
train.py
  └─ make_env()
       └─ BulletHellEnv(render_mode=None)      ← env/bullet_hell_env.py
            └─ Game(headless=True)              ← game/game.py
SB3 PPO 每個 timestep：
  → env.step(action)
       → game._tick(dx, dy) × 4
       → _capture_frame() → numpy array
       → RewardCalculator.calculate()
  ← (obs, reward, done, info)
  → CNN forward pass（GPU）
  → PPO update
```

**超參數**

| 參數 | 值 |
|---|---|
| n_steps | 2048 |
| batch_size | 64 |
| n_epochs | 10 |
| learning_rate | 2.5e-4 |
| gamma | 0.99 |
| clip_range | 0.2 |
| total_timesteps | 1M（驗證）→ 3M（正式） |

**CNN 架構（SB3 內建 NatureCNN）**

```
Input (12, 112, 84)  ← 4 幀 × RGB，channel-first
  → Conv2d(12, 32, kernel=8, stride=4) + ReLU
  → Conv2d(32, 64, kernel=4, stride=2) + ReLU
  → Conv2d(64, 64, kernel=3, stride=1) + ReLU
  → Flatten → Linear(?, 512)
  → Actor head（輸出動作機率）
  → Critic head（輸出狀態價值）
```

**Frame Stacking**

疊 **4 幀**讓 CNN 推斷子彈速度與方向，並搭配 **Frame Skip = 4**（環境層參數，訓練與推論均生效）

**Curriculum Learning（暫時跳過）**

第一版使用固定難度（遊戲內建 STAGE 系統自動提升），目標先達到超越人類水準。
課程學習留待 baseline 跑通後再加入。規劃階段如下：

- 階段一：只有 Drone + 直線彈，低密度
- 階段二：加入 Shooter + 扇形 / 瞄準彈
- 階段三：加入 Sniper + 螺旋彈


#### 4. 展示層

執行 `evaluate.py`，載入訓練好的模型並開視窗顯示 agent 遊玩畫面。

每局結束於終端機印出 score、hp、total reward。

---

## 三、實驗設計

### 評估指標

- 累積 Reward（Cumulative Reward）：訓練過程主要指標
- 平均存活時間（秒）：直觀反映閃避能力
- 平均每局擊殺數：反映攻擊積極性
- Policy Entropy H(πθ)：監控從探索到確定性策略的收斂過程

---



*最後更新：2026-06-02*
