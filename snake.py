"""Simple Snake game using Pygame.

Controls:
- Arrow keys or WASD to move.
- R to restart after game over.
- Esc or window close to quit.
"""

import pygame
import random
import sys

# Configuration
CELL_SIZE = 20
GRID_WIDTH = 32   # window width in cells -> 32 * 20 = 640
GRID_HEIGHT = 24  # window height in cells -> 24 * 20 = 480
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
RED = (220, 40, 40)
YELLOW = (230, 200, 0)

# Movement directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Game speed settings
BASE_MOVE_DELAY = 140  # milliseconds between automatic moves at start
SPEEDUP_EVERY = 3      # every N food eaten, speed up
SPEEDUP_AMOUNT = 8     # reduce delay by this many ms per speedup (to a limit)
MIN_MOVE_DELAY = 40    # cap to prevent being too fast

def place_food(snake):
    """Return a random cell (x,y) not occupied by the snake."""
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos not in snake:
            return pos

def draw_rect_cell(surface, color, cell):
    x, y = cell
    pygame.draw.rect(
        surface,
        color,
        pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    )

def draw_grid(surface):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(surface, DARK_GRAY, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, DARK_GRAY, (0, y), (WINDOW_WIDTH, y))

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    big_font = pygame.font.SysFont(None, 64)

    def reset_game():
        # Snake starts in middle, length 3, moving right
        mid_x = GRID_WIDTH // 2
        mid_y = GRID_HEIGHT // 2
        snake = [(mid_x - i, mid_y) for i in range(3)]
        direction = RIGHT
        food = place_food(snake)
        score = 0
        move_delay = BASE_MOVE_DELAY
        return snake, direction, food, score, move_delay

    snake, direction, food, score, move_delay = reset_game()
    last_move_time = pygame.time.get_ticks()
    running = True
    game_over = False
    allow_direction_change = True  # prevent multiple direction changes per tick

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if not game_over:
                    # Map keys to directions; prevent reversing
                    if event.key in (pygame.K_UP, pygame.K_w):
                        if direction != DOWN and allow_direction_change:
                            direction = UP
                            allow_direction_change = False
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        if direction != UP and allow_direction_change:
                            direction = DOWN
                            allow_direction_change = False
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        if direction != RIGHT and allow_direction_change:
                            direction = LEFT
                            allow_direction_change = False
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        if direction != LEFT and allow_direction_change:
                            direction = RIGHT
                            allow_direction_change = False
                else:
                    # On game over: press R to restart
                    if event.key == pygame.K_r:
                        snake, direction, food, score, move_delay = reset_game()
                        game_over = False
                        last_move_time = pygame.time.get_ticks()

        # Update snake position on timer
        if not game_over and now - last_move_time >= move_delay:
            last_move_time = now
            allow_direction_change = True

            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            # Check wall collision
            if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
                    new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
                game_over = True
            # Check self collision
            elif new_head in snake:
                game_over = True
            else:
                snake.insert(0, new_head)
                if new_head == food:
                    score += 1
                    food = place_food(snake)
                    # speed up occasionally
                    if score % SPEEDUP_EVERY == 0:
                        move_delay = max(MIN_MOVE_DELAY, move_delay - SPEEDUP_AMOUNT)
                else:
                    snake.pop()  # move without growing

        # Draw
        screen.fill(BLACK)
        draw_grid(screen)

        # draw food
        draw_rect_cell(screen, RED, food)

        # draw snake (head brighter)
        if snake:
            draw_rect_cell(screen, YELLOW, snake[0])
            for seg in snake[1:]:
                draw_rect_cell(screen, GREEN, seg)

        # HUD: score
        score_surf = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_surf, (8, 8))

        # If game over, overlay message
        if game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))  # translucent black
            screen.blit(overlay, (0, 0))
            go_surf = big_font.render("Game Over", True, WHITE)
            go_rect = go_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
            screen.blit(go_surf, go_rect)

            score_msg = font.render(f"Final Score: {score}", True, WHITE)
            score_rect = score_msg.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 15))
            screen.blit(score_msg, score_rect)

            hint_msg = font.render("Press R to restart or Esc to quit", True, WHITE)
            hint_rect = hint_msg.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 55))
            screen.blit(hint_msg, hint_rect)

        pygame.display.flip()
        clock.tick(60)  # limit event rate / rendering

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()