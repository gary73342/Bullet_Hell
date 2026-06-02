from stable_baselines3 import PPO
from env import BulletHellEnv

MODEL_PATH = "models/ppo_bullet_hell_final"


def evaluate():
    env = BulletHellEnv(render_mode="human")
    model = PPO.load(MODEL_PATH)

    episode = 0
    while True:
        obs, _ = env.reset()
        episode += 1
        total_reward = 0.0

        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env.step(action)
            total_reward += reward

            if done:
                print(f"Episode {episode} | score={info['score']} | hp={info['hp']} | reward={total_reward:.1f}")
                break


if __name__ == "__main__":
    evaluate()
