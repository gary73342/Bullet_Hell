from env import BulletHellEnv
import numpy as np

def test_env():
    print("建立環境...")
    env = BulletHellEnv(render_mode=None)

    print(f"動作空間：{env.action_space}")
    print(f"觀測空間：{env.observation_space.shape}")

    print("\n--- reset() ---")
    obs, info = env.reset()
    print(f"obs.shape：{obs.shape}")
    print(f"obs.dtype：{obs.dtype}")
    print(f"obs min/max：{obs.min()} / {obs.max()}")

    print("\n--- step() × 10 ---")
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"step {i+1:02d} | action={action} | reward={reward:.4f} | done={terminated} | hp={info['hp']} | score={info['score']}")
        if terminated:
            print("遊戲結束，提前停止")
            break

    print(f"\n最終 obs.shape：{obs.shape}")
    print(f"觀測空間符合：{obs.shape == tuple(env.observation_space.shape)}")

    env.close()
    print("\n測試完成")

if __name__ == "__main__":
    test_env()
