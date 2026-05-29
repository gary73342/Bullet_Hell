import pygame

# 畫面
SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 640
FPS           = 60
TITLE         = "Bullet Hell"

# 顏色
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
CYAN       = (0,   220, 255)   # 我方戰機
RED        = (220, 50,  50)    # 敵方戰機
YELLOW     = (255, 230, 0)     # 我方子彈（之後用）
PINK       = (255, 80,  160)   # 敵方子彈（之後用）
GRAY       = (160, 160, 160)   # UI 文字

# 玩家
PLAYER_SPEED     = 5
PLAYER_HP        = 10
PLAYER_MAX_LEVEL = 6
PLAYER_KILLS_PER_LEVEL = 15

# 玩家子彈
PLAYER_BULLET_SPEED    = 10
PLAYER_FIRE_INTERVAL   = 8    # 每幾幀射一顆

# 敵人（Drone）
DRONE_SPEED   = 2
DRONE_HP      = 1
DRONE_SCORE   = 100
DRONE_SPAWN_INTERVAL = 90   # 每幾幀生成一隻（60fps → 約1.5秒）

# 敵人子彈
ENEMY_BULLET_SPEED   = 4
DRONE_FIRE_INTERVAL  = 90   # Drone 每幾幀射擊一次（各自獨立計時）

# 星空背景
STAR_COUNT    = 30
STAR_SPEED_MIN = 1
STAR_SPEED_MAX = 3

# 玩家無敵幀
PLAYER_INVINCIBLE_FRAMES = 45   # 0.75 秒（60fps × 0.75）
