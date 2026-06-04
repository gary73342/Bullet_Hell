# Bullet Hell — Deep Reinforcement Learning

近代人工智慧期末專題。使用 PPO 訓練 AI 玩兩款 Bullet Hell 遊戲。

---

## 兩款遊戲

### 原版（Original）

位於 `game/`，為自行以 Pygame 實作的 Bullet Hell。

- 玩家可 8 方向移動，自動射擊
- 敵人以編隊形式從上方生成，射出子彈
- 場上有血包可拾取
- 關卡隨分數推進，難度逐漸提升
- Gymnasium 環境包裝：`env/bullet_hell_env.py`

### 外部克隆版（Ext）

位於 `game_ext/`，克隆自 GitHub 上的開源專案 [Sacred Curry Shooter](https://www.pygame.org/project/937)（Touhou 風格俯視射擊），原作者已附帶 DQN 訓練框架，本專案將其改接至自訂的 PPO 環境。

- 原作遊戲邏輯保持不變，移除幀率限制以加速訓練
- Gymnasium 環境包裝：`env_ext/ext_env.py`

---

## 架構：CNN + PPO

使用 **Stable Baselines3** 的 `PPO` 搭配 `MultiInputPolicy`，觀測空間為 Dict，同時輸入影像與結構化向量。

### 觀測空間

| 鍵 | 形狀 | 說明 |
|---|---|---|
| `pixels` | `(12, H, W)` | 4 幀 RGB 堆疊（frame stacking），CNN 輸入 |
| `state` | `(VEC_DIM,)` | 結構化向量：玩家座標、血量、最近子彈與敵人座標（正規化至 0~1）|

- 原版解析度：`84 × 112`，VEC_DIM = 69
- 外部版解析度：`84 × 84`，VEC_DIM = 62

訓練使用 4 個並行環境（`SubprocVecEnv`），每次訓練預設跑 100 萬步，每 10 萬步存一次 checkpoint。

---

## 需求套件

詳細見 requirements.txt

---

## 訓練

```bash
# 原版遊戲
python train.py --env original

# 外部克隆版
python train.py --env ext

# 自訂訓練名稱（儲存至 models/<run-name>/）
python train.py --env original --run-name exp_01
```

---

## 評估

```bash
# 原版遊戲（使用預設模型）
python evaluate.py --env original

# 外部克隆版（使用預設模型）
python evaluate.py --env ext

# 指定模型路徑
python evaluate.py --env original --model models/train4/ppo_bullet_hell_4800000_steps
python evaluate.py --env ext --model models/ext_run/ppo_bullet_hell_final
```

評估時會開啟 Pygame 視窗即時顯示，按 `ESC` 或關閉視窗結束。

---

## 專案結構

```
MAI/
├── game/           # 原版 Pygame 遊戲
├── game_ext/       # 外部克隆版遊戲
├── env/            # 原版 Gymnasium 環境包裝
├── env_ext/        # 外部版 Gymnasium 環境包裝
├── models/         # 訓練產出的模型與 TensorBoard log
├── logs/           # 開發日誌
├── train.py        # 訓練入口
├── evaluate.py     # 評估入口
├── main.py         # 遊戲人工遊玩入口
└── requirements.txt
```
