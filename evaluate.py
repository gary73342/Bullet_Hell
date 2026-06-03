import pygame
from stable_baselines3 import PPO
from env import BulletHellEnv

MODEL_PATH = "models/train2/ppo_bullet_hell_final"


def evaluate():
    env = BulletHellEnv(render_mode="human")
    model = PPO.load(MODEL_PATH)

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
                    print(f"Episode {episode} | score={info['score']} | hp={info['hp']} | reward={total_reward:.1f}")
                    break
    finally:
        env.close()


if __name__ == "__main__":
    evaluate()
