import argparse
import os
import time
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions.categorical import Categorical
from torch.utils.tensorboard import SummaryWriter

from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from env import BulletHellEnv
from env_ext import ExtBulletHellEnv

# ─── 1. 超參數設定 ───
TOTAL_TIMESTEPS = 1_000_000
SAVE_FREQ       = 100_000
MODEL_NAME      = "ppo_bullet_hell"
N_ENVS          = 4

ENV_CLASSES = {
    "original": BulletHellEnv,
    "ext":      ExtBulletHellEnv,
}

def make_env(env_type):
    EnvClass = ENV_CLASSES[env_type]
    def _init():
        return EnvClass(render_mode=None)
    return _init

# ─── 2. 雙模態卷積神經網路 (完全對應你的 Dict 觀測空間) ───
class BulletHellActorCritic(nn.Module):
    def __init__(self, num_actions=9):
        super().__init__()
        
        # (1) 圖片特徵提取 (CNN) -> 處理 (12, 112, 84) 的畫面
        self.cnn = nn.Sequential(
            nn.Conv2d(12, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        
        # (2) 結構化狀態特徵提取 (MLP) -> 處理 69 維向量
        self.mlp = nn.Sequential(
            nn.Linear(69, 64),
            nn.ReLU()
        )
        
        # 融合後的特徵全連接層 (CNN 平坦化後為 64*10*7 = 4480 維)
        self.feature_linear = nn.Sequential(
            nn.Linear(4480 + 64, 512),
            nn.ReLU()
        )
        
        # Actor 輸出 9 個動作機率，Critic 輸出 1 個局勢估值
        self.actor = nn.Linear(512, num_actions)
        self.critic = nn.Linear(512, 1)

    def forward(self, pixels, state):
        # 圖片正規化到 [0, 1]
        cnn_features = self.cnn(pixels.float() / 255.0)
        mlp_features = self.mlp(state)
        
        # 特徵拼接 (Concatenate)
        combined = torch.cat([cnn_features, mlp_features], dim=1)
        shared_features = self.feature_linear(combined)
        
        logits = self.actor(shared_features)
        value = self.critic(shared_features)
        return logits, value

# ─── 3. 手刻原生 PPO 訓練邏輯 ───
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", type=str, default=None, help="訓練名稱")
    parser.add_argument("--env", type=str, default="original", choices=["original", "ext"], help="環境選擇")
    args = parser.parse_args()

    run_name = args.run_name or datetime.now().strftime("train_%Y%m%d_%H%M%S")
    run_dir  = os.path.join("models", run_name)
    os.makedirs(run_dir, exist_ok=True)
    print(f"訓練資料夾：{run_dir}")
    print(f"訓練環境：{args.env}")

    # 初始化平行環境與日誌
    env = SubprocVecEnv([make_env(args.env) for _ in range(N_ENVS)])
    env = VecMonitor(env, filename=os.path.join(run_dir, "monitor"))

    # 硬體配置與網路實例化
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy = BulletHellActorCritic(num_actions=9).to(device)
    
    # 這裡對齊你原先設定的超參數
    learning_rate = 2.5e-4
    n_steps       = 2048
    batch_size    = 256
    n_epochs      = 10
    gamma         = 0.995
    gae_lambda    = 0.90
    clip_range    = 0.2
    ent_coef      = 0.005
    
    optimizer = optim.Adam(policy.parameters(), lr=learning_rate, eps=1e-5)
    writer = SummaryWriter(os.path.join(run_dir, "tensorboard"))

    # 建立 Rollout Buffer 儲存空間
    storage_pixels = torch.zeros((n_steps, N_ENVS, 12, 112, 84), dtype=torch.uint8).to(device)
    storage_state  = torch.zeros((n_steps, N_ENVS, 69), dtype=torch.float32).to(device)
    storage_actions = torch.zeros((n_steps, N_ENVS)).to(device)
    storage_logprobs = torch.zeros((n_steps, N_ENVS)).to(device)
    storage_rewards = torch.zeros((n_steps, N_ENVS)).to(device)
    storage_dones   = torch.zeros((n_steps, N_ENVS)).to(device)
    storage_values  = torch.zeros((n_steps, N_ENVS)).to(device)

    # 啟動環境
    obs = env.reset() # 回傳 Dict: {'pixels': ..., 'state': ...}
    global_step = 0
    next_save_step = SAVE_FREQ

    print("開始原生 Python PPO 訓練 🚀")
    
    while global_step < TOTAL_TIMESTEPS:
        # ─── Step A: 收集經驗 (Rollout) ───
        policy.eval()
        for step in range(n_steps):
            global_step += N_ENVS
            
            # 將環境資料轉成 Tensor 並存入 Buffer
            t_pixels = torch.tensor(obs['pixels']).to(device)
            t_state  = torch.tensor(obs['state']).to(device)
            storage_pixels[step] = t_pixels
            storage_state[step]  = t_state

            with torch.no_grad():
                logits, value = policy(t_pixels, t_state)
                probs = Categorical(logits=logits)
                action = probs.sample()
                logprob = probs.log_prob(action)
            
            storage_actions[step]  = action
            storage_logprobs[step] = logprob
            storage_values[step]   = value.squeeze(-1)

            # 執行環境步進
            next_obs, reward, done, info = env.step(action.cpu().numpy())
            storage_rewards[step] = torch.tensor(reward, dtype=torch.float32).to(device)
            storage_dones[step]   = torch.tensor(done, dtype=torch.float32).to(device)
            
            obs = next_obs

        # ─── Step B: 計算 GAE 優勢函數 ───
        policy.eval()
        with torch.no_grad():
            _, next_value = policy(torch.tensor(obs['pixels']).to(device), torch.tensor(obs['state']).to(device))
            next_value = next_value.squeeze(-1)
        
        advantages = torch.zeros_like(storage_rewards).to(device)
        lastgaelam = 0
        for t in reversed(range(n_steps)):
            if t == n_steps - 1:
                nextnonterminal = 1.0 - storage_dones[t]
                nextvalues = next_value
            else:
                nextnonterminal = 1.0 - storage_dones[t]
                nextvalues = storage_values[t + 1]
            
            # 貝爾曼公式殘差 Delta
            delta = storage_rewards[t] + gamma * nextvalues * nextnonterminal - storage_values[t]
            advantages[t] = lastgaelam = delta + gamma * gae_lambda * nextnonterminal * lastgaelam
        
        returns = advantages + storage_values

        # 拉平資料集以供 Mini-batch 梯度下降
        b_pixels   = storage_pixels.reshape((-1, 12, 112, 84))
        b_state    = storage_state.reshape((-1, 69))
        b_actions  = storage_actions.reshape(-1)
        b_logprobs = storage_logprobs.reshape(-1)
        b_advantages = advantages.reshape(-1)
        b_returns  = returns.reshape(-1)
        b_values   = storage_values.reshape(-1)

        # ─── Step C: PPO 損失函數與權重更新 (優化階段) ───
        policy.train()
        b_inds = np.arange(n_steps * N_ENVS)
        
        for epoch in range(n_epochs):
            np.random.shuffle(b_inds)
            for start in range(0, len(b_inds), batch_size):
                end = start + batch_size
                mb_inds = b_inds[start:end]

                # 預測新動作機率與新價值
                logits, value = policy(b_pixels[mb_inds], b_state[mb_inds])
                probs = Categorical(logits=logits)
                
                new_logprob = probs.log_prob(b_actions[mb_inds])
                entropy = probs.entropy().mean()

                # 計算機率比值 Ratio
                logratio = new_logprob - b_logprobs[mb_inds]
                ratio = logratio.exp()

                # 歸一化優勢值
                mb_advantages = b_advantages[mb_inds]
                mb_advantages = (mb_advantages - mb_advantages.mean()) / (mb_advantages.std() + 1e-8)

                # 1. Policy Loss (Actor 裁剪損失)
                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range)
                actor_loss = torch.max(pg_loss1, pg_loss2).mean()

                # 2. Value Loss (Critic 均方誤差損失)
                value_loss = 0.5 * ((value.squeeze(-1) - b_returns[mb_inds]) ** 2).mean()

                # 總損失公式：結合優化目標並加入熵機制鼓勵探索
                loss = actor_loss + value_loss - ent_coef * entropy

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(policy.parameters(), 0.5) # 梯度裁剪防止數值爆炸
                optimizer.step()

        # 寫入 TensorBoard 記錄日誌
        writer.add_scalar("losses/total_loss", loss.item(), global_step)
        writer.add_scalar("losses/actor_loss", actor_loss.item(), global_step)
        writer.add_scalar("losses/value_loss", value_loss.item(), global_step)
        print(f"步數: {global_step}/{TOTAL_TIMESTEPS} | 當前 Loss: {loss.item():.4f}")

        # ─── Step D: 定期儲存檢查點 ───
        if global_step >= next_save_step:
            ckpt_path = os.path.join(run_dir, f"{MODEL_NAME}_{next_save_step}_steps.pt")
            torch.save(policy.state_dict(), ckpt_path)
            print(f"💾 已儲存檢查點：{ckpt_path}")
            next_save_step += SAVE_FREQ

    # 儲存最終模型
    final_path = os.path.join(run_dir, f"{MODEL_NAME}_final.pt")
    torch.save(policy.state_dict(), final_path)
    env.close()
    writer.close()
    print("🎉 訓練完全成功結束！")