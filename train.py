from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor

from env import BulletHellEnv

TOTAL_TIMESTEPS = 1_000_000
SAVE_FREQ       = 100_000
MODEL_DIR       = "models"
MODEL_NAME      = "ppo_bullet_hell"


def make_env():
    env = BulletHellEnv(render_mode=None)
    return Monitor(env, filename=f"{MODEL_DIR}/monitor")


if __name__ == "__main__":
    env = make_env()

    model = PPO(
        policy="CnnPolicy",
        env=env,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        learning_rate=2.5e-4,
        gamma=0.99,
        clip_range=0.2,
        tensorboard_log=f"{MODEL_DIR}/tensorboard",
        device="auto",
        verbose=1,
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=SAVE_FREQ,
        save_path=MODEL_DIR,
        name_prefix=MODEL_NAME,
    )

    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=checkpoint_cb,
        progress_bar=True,
    )

    model.save(f"{MODEL_DIR}/{MODEL_NAME}_final")
    env.close()
    print("訓練完成")
