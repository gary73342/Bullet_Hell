import argparse
import os
from datetime import datetime

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from env import BulletHellEnv
from env_ext import ExtBulletHellEnv

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", type=str, default=None,
                        help="訓練名稱，例如 exp_lr0001；不填則自動用時間戳")
    parser.add_argument("--env", type=str, default="original", choices=["original", "ext"],
                        help="訓練環境：original（預設）或 ext（外部遊戲）")
    args = parser.parse_args()

    run_name = args.run_name or datetime.now().strftime("train_%Y%m%d_%H%M%S")
    run_dir  = os.path.join("models", run_name)
    os.makedirs(run_dir, exist_ok=True)
    print(f"訓練資料夾：{run_dir}")
    print(f"訓練環境：{args.env}")

    env = SubprocVecEnv([make_env(args.env) for _ in range(N_ENVS)])
    env = VecMonitor(env, filename=os.path.join(run_dir, "monitor"))

    model = PPO(
        policy="MultiInputPolicy",
        env=env,
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        learning_rate=2.5e-4,
        gamma=0.995,
        gae_lambda=0.90,
        clip_range=0.2,
        ent_coef=0.005,
        tensorboard_log=os.path.join(run_dir, "tensorboard"),
        device="auto",
        verbose=1,
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=SAVE_FREQ // N_ENVS,
        save_path=run_dir,
        name_prefix=MODEL_NAME,
    )

    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=checkpoint_cb,
        progress_bar=True,
    )

    model.save(os.path.join(run_dir, f"{MODEL_NAME}_final"))
    env.close()
    print("訓練完成")
