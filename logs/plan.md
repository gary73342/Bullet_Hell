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

#### 2. Gym 包裝層（Gymnasium）

實作三個核心方法：

```python
def reset(self)  → 回傳初始觀測值
def step(self, action)  → 執行動作，回傳 (obs, reward, done, info)
def render(self)  → 訓練時關閉，展示時開啟
```

**觀測空間（待定）**

| 版本 | 觀測方式 | Shape | Policy |
|------|----------|-------|--------|
| Baseline | 向量（玩家座標、子彈相對位置等） | (23,) | MlpPolicy |
| CNN n=1 | 彩色截圖 | (H, W, 3) | CnnPolicy |
| CNN n=4 | 彩色截圖 × frame stacking | (H, W, 12) | CnnPolicy |

解析度待定，候選：84×112、120×160、168×224（依遊戲視窗比例等比縮小）

**動作空間**

```
Discrete(5)：不動 / 上 / 下 / 左 / 右
射擊設為自動，不佔動作維度
```

**Reward Function**
目前暫定
```python
reward  = +0.01 * 每幀存活        # Rtime：鼓勵活久
reward += +5.0  * 擊殺普通敵人    # Rkill
reward += +20.0 * 擊殺 Boss       # Rkill（Boss）
reward += -10.0 * 被子彈擊中      # Rpenalty
reward += -50.0 * 死亡            # Rpenalty（終局）
```

#### 3. 訓練層

**演算法：** PPO（Proximal Policy Optimization）

**套件：** 待定（SB3 或自行實作）

- 若使用 SB3：直接呼叫 `PPO("CnnPolicy", env)`，CNN 架構可自訂
- 若自行實作：使用 PyTorch 手刻 CNN + PPO，完整控制所有細節

**CNN 架構（參考 NatureCNN）**

```
Input (H, W, C)
  → Conv2d(C,  32, kernel=8, stride=4) + ReLU
  → Conv2d(32, 64, kernel=4, stride=2) + ReLU
  → Conv2d(64, 64, kernel=3, stride=1) + ReLU
  → Flatten
  → Linear(?, 512)
  → Actor head（輸出動作機率）
  → Critic head（輸出狀態價值）
```

**Frame Stacking**

疊 N 幀讓 CNN 推斷子彈速度與方向，N 待定（候選：2、4）

**Curriculum Learning**

逐步提升難度，避免 agent 一開始面對過難環境：

- 階段一：只有 Drone + 直線彈，低密度
- 階段二：加入 Shooter + 扇形 / 瞄準彈
- 階段三：加入 Sniper + 螺旋彈
- 階段四：全敵人 + 高密度彈幕
- 階段五：Boss 關卡

觸發條件待定（固定步數 or 依表現自動升級）

#### 4. 展示層

```python
model = PPO.load("bullet_hell_agent")
obs, _ = env.reset()
while True:
    action, _ = model.predict(obs)
    obs, reward, done, _, _ = env.step(action)
    if done:
        obs, _ = env.reset()
```

---

## 三、實驗設計

### 對照實驗

| 實驗 | 變數 | 目的 |
|------|------|------|
| MLP vs CNN | 觀測方式（向量 vs pixel） | 驗證 CNN 在 Sniper 警示線等空間特徵上的優勢 |
| CNN n=1 vs n=4 | Frame stacking 幀數 | 驗證速度資訊對閃避的影響 |
| Curriculum vs Non-curriculum | 有無課程學習 | 驗證逐步升難度對最終表現的影響 |
| Reward ablation | 純存活 vs 存活 + 擊殺 | 驗證 reward 設計對行為的影響 |

### 評估指標

- 累積 Reward（Cumulative Reward）：訓練過程主要指標
- 平均存活時間（秒）：直觀反映閃避能力
- 平均每局擊殺數：反映攻擊積極性
- Policy Entropy H(πθ)：監控從探索到確定性策略的收斂過程

---

## 四、時間排程（2 週）

### 第一週：環境建置 + Baseline

| 天數 | 工作項目 | 負責 |
|------|----------|------|
| Day 1–2 | 安裝環境（Python、Pygame、Gymnasium、SB3 / PyTorch） | 雙人 |
| Day 2–4 | 開發 Pygame 遊戲（玩家、子彈、敵人基本邏輯） | 人 A |
| Day 4–5 | 設計 Gym 包裝層（reset / step / reward） | 人 B |
| Day 6 | 第一次訓練跑通（MLP baseline） | 雙人 |
| Day 7 | 驗證 baseline reward 曲線上升，確認環境正確 | 雙人 |

### 第二週：實驗 + 報告

| 天數 | 工作項目 | 負責 |
|------|----------|------|
| Day 8–9 | CNN 版本訓練 + Curriculum Learning 實作 | 人 A |
| Day 10–11 | 對照實驗（frame stacking、reward ablation） | 人 B |
| Day 12 | 收集數據、繪製訓練曲線與結果圖表 | 雙人 |
| Day 12–13 | 撰寫期末報告 | 雙人 |
| Day 13–14 | 製作簡報 + 錄製 Demo 影片 | 雙人 |

---

## 五、待決定事項

以下細節尚未確定，後續討論後補上：

- [ ] 遊戲視窗解析度
- [ ] 觀測解析度（84×112 / 120×160 / 168×224）
- [ ] Frame stacking 幀數（2 or 4）
- [ ] 訓練套件（SB3 or 自行實作 PPO）
- [ ] CNN 架構細節（filter 數、是否加 BatchNorm）
- [ ] Curriculum 升級觸發條件（固定步數 or 依表現）
- [ ] 兩人分工細節

---


*最後更新：2026 年 5 月*
