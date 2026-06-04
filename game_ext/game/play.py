import main
import pygame

w = main.Main()

while True:
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        action = 0
    elif keys[pygame.K_RIGHT]:
        action = 1
    else:
        action = 3
    reward, img, death = w.MainLoop(action)
    if death:
        break
