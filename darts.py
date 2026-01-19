"""
Darts - simple Pygame implementation

Controls:
- Move mouse to aim.
- Hold LEFT MOUSE BUTTON to charge power (the power bar fills).
- Release LEFT MOUSE BUTTON to throw.
- R to restart the game.
- Esc or window close to quit.

Game rules:
- Start at START_SCORE (default 301).
- Each turn you get up to 3 darts.
- Each dart subtracts points immediately.
- If a throw makes the score negative, it's a "bust": the turn ends and your score reverts to the value at the start of the turn.
- If score reaches exactly 0 you win.
"""
import math
import random
import sys
import pygame

# Configuration
START_SCORE = 301
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
FPS = 60

# Board layout & proportions
BOARD_RADIUS = 300
BOARD_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)

BULL_INNER_RADIUS = int(0.05 * BOARD_RADIUS)   # 50
BULL_OUTER_RADIUS = int(0.09 * BOARD_RADIUS)   # 90-ish
TRIPLE_INNER = int(0.52 * BOARD_RADIUS)
TRIPLE_OUTER = int(0.58 * BOARD_RADIUS)
DOUBLE_INNER = int(0.85 * BOARD_RADIUS)
DOUBLE_OUTER = int(0.92 * BOARD_RADIUS)

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
DARK_GRAY = (40, 40, 40)
RED = (200, 40, 40)
GREEN = (30, 140, 40)
GOLD = (230, 190, 70)
BLUE = (50, 80, 160)
BG = (24, 24, 28)
LIGHT = (200, 200, 200)

# Sector numbers clockwise starting at angle -90 degrees (top = 20)
SECTOR_ORDER = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17,
                3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

# Throw parameters
POWER_MAX_TIME = 1.8  # seconds to reach full power
MIN_INACCURACY = 6    # pixels
MAX_INACCURACY = 30   # pixels


def angle_to_sector(angle):
    """
    angle: radians, 0 along +x axis, increasing counter-clockwise.
    We want 0 to correspond to the right; top (12 o'clock) is -pi/2.
    SECTOR_ORDER indexing: sector 0 corresponds to top (20).
    """
    # Convert to angle measured from top (12 o'clock), clockwise
    # top = -pi/2 -> we want t=0
    t = -angle - math.pi / 2
    # normalize to [0, 2pi)
    t = t % (2 * math.pi)
    # each sector spans 2*pi/20
    sector_idx = int(t / (2 * math.pi) * 20) % 20
    return SECTOR_ORDER[sector_idx], sector_idx


def score_from_pos(x, y):
    """
    Given a point (x,y) in screen coordinates, compute darts score.
    Returns (value, multiplier, description)
    """
    cx, cy = BOARD_CENTER
    dx = x - cx
    dy = y - cy
    r = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)  # standard arctan2

    # bullseye?
    if r <= BULL_INNER_RADIUS:
        return 50, 1, "Bullseye (50)"
    if r <= BULL_OUTER_RADIUS:
        return 25, 1, "Outer Bull (25)"

    # outside board
    if r > DOUBLE_OUTER:
        return 0, 1, "Miss (0)"

    # sector hit: determine base number and then multiplier by ring
    base, idx = angle_to_sector(angle)

    # triple ring?
    if TRIPLE_INNER <= r <= TRIPLE_OUTER:
        return base * 3, 3, f"Triple {base} ({base*3})"
    # double ring?
    if DOUBLE_INNER <= r <= DOUBLE_OUTER:
        return base * 2, 2, f"Double {base} ({base*2})"
    # single number
    return base, 1, f"Single {base} ({base})"


def draw_board(surface):
    cx, cy = BOARD_CENTER
    # background circles
    pygame.draw.circle(surface, BLACK, (cx, cy), BOARD_RADIUS)
    # outer double ring
    pygame.draw.circle(surface, DARK_GRAY, (cx, cy), DOUBLE_OUTER)
    pygame.draw.circle(surface, BG, (cx, cy), DOUBLE_INNER)
    # triple ring
    pygame.draw.circle(surface, DARK_GRAY, (cx, cy), TRIPLE_OUTER)
    pygame.draw.circle(surface, BG, (cx, cy), TRIPLE_INNER)
    # bull rings
    pygame.draw.circle(surface, RED, (cx, cy), BULL_INNER_RADIUS)
    pygame.draw.circle(surface, GREEN, (cx, cy), BULL_OUTER_RADIUS, 3)

    # sector wedges (alternate colors)
    for i in range(20):
        a1 = -math.pi/2 + (i) * (2*math.pi/20)
        a2 = -math.pi/2 + (i+1) * (2*math.pi/20)
        # choose color alternation
        outer_color = (20, 20, 20) if i % 2 == 0 else (60, 60, 60)
        inner_color = (60, 10, 10) if i % 2 == 0 else (10, 60, 10)

        # draw double wedge
        pygame.draw.polygon(surface, outer_color, [
            (cx + DOUBLE_INNER * math.cos(a1), cy + DOUBLE_INNER * math.sin(a1)),
            (cx + DOUBLE_OUTER * math.cos(a1), cy + DOUBLE_OUTER * math.sin(a1)),
            (cx + DOUBLE_OUTER * math.cos(a2), cy + DOUBLE_OUTER * math.sin(a2)),
            (cx + DOUBLE_INNER * math.cos(a2), cy + DOUBLE_INNER * math.sin(a2))
        ])
        # draw triple wedge
        pygame.draw.polygon(surface, inner_color, [
            (cx + TRIPLE_INNER * math.cos(a1), cy + TRIPLE_INNER * math.sin(a1)),
            (cx + TRIPLE_OUTER * math.cos(a1), cy + TRIPLE_OUTER * math.sin(a1)),
            (cx + TRIPLE_OUTER * math.cos(a2), cy + TRIPLE_OUTER * math.sin(a2)),
            (cx + TRIPLE_INNER * math.cos(a2), cy + TRIPLE_INNER * math.sin(a2))
        ])

    # number ring (draw the numbers)
    font = pygame.font.SysFont(None, 22, bold=True)
    radius_for_numbers = int(DOUBLE_OUTER * 1.03)
    for i, num in enumerate(SECTOR_ORDER):
        ang = -math.pi/2 + (i + 0.5) * (2*math.pi/20)
        tx = cx + radius_for_numbers * math.cos(ang)
        ty = cy + radius_for_numbers * math.sin(ang)
        text = font.render(str(num), True, LIGHT)
        rect = text.get_rect(center=(tx, ty))
        surface.blit(text, rect)


def draw_power_bar(surface, power_ratio, pos):
    x, y = pos
    w, h = 220, 18
    pygame.draw.rect(surface, DARK_GRAY, (x, y, w, h))
    inner_w = int(power_ratio * w)
    pygame.draw.rect(surface, RED, (x, y, inner_w, h))
    pygame.draw.rect(surface, LIGHT, (x, y, w, h), 2)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Darts")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 26)
    big_font = pygame.font.SysFont(None, 48, bold=True)
    small = pygame.font.SysFont(None, 20)

    def reset():
        return {
            "score": START_SCORE,
            "turn_start_score": START_SCORE,
            "darts_this_turn": 0,
            "throws": [],  # list of (x,y,score,desc)
            "charging": False,
            "charge_start": 0.0,
            "game_over": False,
            "winner": False,
            "message": "",
        }

    state = reset()
    running = True

    # for simple throw animation: store last thrown positions to draw small dart circles
    last_throw_anim = []  # list of (x,y,age_frames)

    while running:
        dt = clock.tick(FPS) / 1000.0
        mx, my = pygame.mouse.get_pos()
        cx, cy = BOARD_CENTER

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    state = reset()
                    last_throw_anim = []

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not state["game_over"]:
                    # start charging
                    state["charging"] = True
                    state["charge_start"] = pygame.time.get_ticks() / 1000.0

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and state["charging"] and not state["game_over"]:
                    # release -> perform throw
                    charge_time = (pygame.time.get_ticks() / 1000.0) - state["charge_start"]
                    power_ratio = min(1.0, max(0.01, charge_time / POWER_MAX_TIME))
                    # compute intended radius from center: full power aims to triple/double area ranges
                    # map power_ratio to [0, 1] radial fraction of board:
                    intended_r = power_ratio * DOUBLE_OUTER
                    # Add randomness (inaccuracy)
                    # Inaccuracy scales between MAX_INACCURACY and MIN_INACCURACY depending on charge_time
                    inacc = MAX_INACCURACY - (MAX_INACCURACY - MIN_INACCURACY) * (power_ratio)
                    # Add radial and angular jitter
                    radial_jitter = random.gauss(0, inacc)
                    angular_jitter = random.gauss(0, math.radians(3 + inacc/4.0))
                    # Calculate final thrown point
                    dx = mx - cx
                    dy = my - cy
                    aim_angle = math.atan2(dy, dx)
                    final_angle = aim_angle + angular_jitter
                    final_r = max(0, intended_r + radial_jitter)
                    final_x = cx + final_r * math.cos(final_angle)
                    final_y = cy + final_r * math.sin(final_angle)

                    val, mult, desc = score_from_pos(final_x, final_y)

                    # Apply scoring: immediate subtraction; bust logic
                    prev_score = state["score"]
                    new_score = prev_score - val

                    busted = False
                    winner = False
                    message = ""

                    # If new_score < 0 -> bust: revert to turn start and end turn
                    if new_score < 0:
                        busted = True
                        state["score"] = state["turn_start_score"]
                        message = f"BUST! Back to {state['score']}"
                    elif new_score == 0:
                        winner = True
                        state["score"] = 0
                        message = "YOU WIN!"
                    else:
                        state["score"] = new_score

                    # record throw
                    state["throws"].append((final_x, final_y, val, mult, desc))
                    last_throw_anim.append([final_x, final_y, 0])

                    # increment darts count unless bust ends turn
                    state["darts_this_turn"] += 1

                    if busted or winner or state["darts_this_turn"] >= 3:
                        # end of turn -> reset darts and set new turn start
                        state["darts_this_turn"] = 0
                        state["turn_start_score"] = state["score"]
                        if winner:
                            state["game_over"] = True
                            state["winner"] = True
                            state["message"] = message
                        elif busted:
                            # end turn due to bust
                            state["message"] = message
                        else:
                            state["message"] = ""  # clear any previous message

                    state["charging"] = False

        # Update animations: age darts
        for anim in last_throw_anim:
            anim[2] += 1
        # prune old ones
        last_throw_anim = [a for a in last_throw_anim if a[2] < FPS * 2.0]

        # draw
        screen.fill((30, 30, 40))
        # left panel for HUD
        hud_w = 260
        pygame.draw.rect(screen, (20, 20, 28), (0, 0, hud_w, WINDOW_HEIGHT))

        # draw dartboard
        draw_board(screen)

        # draw thrown darts as small dots
        for x, y, _, _, _ in state["throws"][-10:]:
            pygame.draw.circle(screen, GOLD, (int(x), int(y)), 6)

        # draw throw animations (fading)
        for x, y, age in last_throw_anim:
            alpha = max(0, 255 - int(age * (255 / (FPS * 1.6))))
            surf = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 235, 120, alpha), (10, 10), 8)
            screen.blit(surf, (x - 10, y - 10))

        # HUD texts
        title = big_font.render("DARTS - Single Player", True, WHITE)
        screen.blit(title, (18, 12))

        score_text = font.render(f"Score: {state['score']}", True, LIGHT)
        screen.blit(score_text, (18, 80))

        start_score_text = small.render(f"Start: {START_SCORE}", True, LIGHT)
        screen.blit(start_score_text, (18, 110))

        darts_text = font.render(f"Darts this turn: {state['darts_this_turn']}/3", True, LIGHT)
        screen.blit(darts_text, (18, 140))

        instr_y = 190
        instrs = [
            "Aim with mouse (move cursor).",
            "Hold LEFT MOUSE to charge power.",
            "Release to throw.",
            "Bust if score < 0 (turn cancelled).",
            "Exact 0 wins!",
            "",
            "Press R to restart, Esc to quit."
        ]
        for i, line in enumerate(instrs):
            screen.blit(small.render(line, True, (200, 200, 200)), (18, instr_y + i * 22))

        # Last throws listing (right of HUD)
        last_section_y = 380
        screen.blit(font.render("Recent Throws:", True, LIGHT), (18, last_section_y))
        for i, t in enumerate(reversed(state["throws"][-6:])):
            x, y, val, mult, desc = t
            s = f"{desc} -> {val}"
            screen.blit(small.render(s, True, (220, 220, 220)), (18, last_section_y + 28 + i * 22))

        # Power bar (if charging)
        if state["charging"]:
            charge_time = (pygame.time.get_ticks() / 1000.0) - state["charge_start"]
            power_ratio = min(1.0, max(0.0, charge_time / POWER_MAX_TIME))
            draw_power_bar(screen, power_ratio, (18, WINDOW_HEIGHT - 60))
            screen.blit(small.render("Power", True, LIGHT), (18, WINDOW_HEIGHT - 86))
        else:
            draw_power_bar(screen, 0.0, (18, WINDOW_HEIGHT - 60))
            screen.blit(small.render("Hold LMB to charge", True, (180, 180, 180)), (18, WINDOW_HEIGHT - 86))

        # crosshair at mouse/aim position
        pygame.draw.line(screen, (180, 180, 180), (mx - 10, my), (mx + 10, my), 1)
        pygame.draw.line(screen, (180, 180, 180), (mx, my - 10), (mx, my + 10), 1)

        # Draw a subtle line from center to mouse to indicate aim
        pygame.draw.line(screen, (100, 100, 150), (cx, cy), (mx, my), 1)

        # Draw center point
        pygame.draw.circle(screen, (220, 220, 220), (cx, cy), 4)

        # If game over, show overlay
        if state["game_over"]:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            win_text = big_font.render(state.get("message", "Game Over"), True, (240, 240, 240))
            rect = win_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
            screen.blit(win_text, rect)

            restart_text = font.render("Press R to restart or Esc to quit", True, (220, 220, 220))
            rrect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
            screen.blit(restart_text, rrect)

        # draw small legend for rings on board corner
        legend_x = cx + BOARD_RADIUS + 10
        legend_y = cy - BOARD_RADIUS + 6
        pygame.draw.rect(screen, (18, 18, 20), (legend_x - 8, legend_y - 6, 180, 120))
        screen.blit(small.render("Board legend:", True, LIGHT), (legend_x, legend_y))
        screen.blit(small.render("Red bull = 50, Green ring = 25", True, (200, 200, 200)),
                    (legend_x, legend_y + 22))
        screen.blit(small.render("Triple ring in middle band", True, (200, 200, 200)),
                    (legend_x, legend_y + 44))
        screen.blit(small.render("Double ring at outer band", True, (200, 200, 200)),
                    (legend_x, legend_y + 66))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()