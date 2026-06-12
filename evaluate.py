import argparse
import pygame
from stable_baselines3 import PPO
from env import BulletHellEnv
from env_ext import ExtBulletHellEnv

DEFAULT_MODELS = {
    "original": "models/train5/ppo_bullet_hell_final",
    "ext":      "models/ext_run/ppo_bullet_hell_final",
}

ENV_CLASSES = {
    "original": BulletHellEnv,
    "ext":      ExtBulletHellEnv,
}


def evaluate(env_type, model_path):
    env = ENV_CLASSES[env_type](render_mode="human")
    model = PPO.load(model_path)

    episode = 0
    try:
        while True:
            obs, _ = env.reset()
            episode += 1
            total_reward = 0.0

            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        return

                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, _, info = env.step(action)
                total_reward += reward

                if done:
                    if env_type == "original":
                        print(f"Episode {episode} | score={info['score']} | hp={info['hp']} | reward={total_reward:.1f}")
                    else:
                        print(f"Episode {episode} | score={info['score']} | reward={total_reward:.1f}")
                    break
    finally:
        env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=str, default="original", choices=["original", "ext"])
    parser.add_argument("--model", type=str, default=None, help="模型路徑（不填則用預設）")
    args = parser.parse_args()

    model_path = args.model or DEFAULT_MODELS[args.env]
    evaluate(args.env, model_path)
