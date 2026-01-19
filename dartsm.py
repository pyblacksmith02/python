"""
Darts - Multiplayer (Hotseat) - Pygame

Features
- Local multiplayer (hotseat) for 2-4 players.
- Each player gets up to 3 darts per turn.
- Configurable starting score (301 or 501) at the start screen.
- Aim with the mouse, hold LEFT MOUSE to charge power, release to throw.
- Bust rules: if a throw makes your score < 0 the turn ends and your score reverts to the start-of-turn value.
- First player to reach exactly 0 wins.
- R to restart at any time, Esc to quit.

Controls (start screen)
- Number keys 2,3,4 to pick number of players
- 3/5 to switch starting score (301/501)
- Space to start game

Controls (in-game)
- Move mouse to aim
- Hold LMB to charge power, release to throw
- R to restart game
- Esc to quit
"""
import math
import random
import sys
import pygame
from dataclasses import dataclass, field
from typing import List, Tuple

# -- Configuration --
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

BOARD_RADIUS = 300
BOARD_CENTER = (WINDOW_WIDTH // 2 + 120, WINDOW_HEIGHT // 2 - 20)

BULL_INNER_RADIUS = int(0.05 * BOARD_RADIUS)
BULL_OUTER_RADIUS = int(0.09 * BOARD_RADIUS)
TRIPLE_INNER = int(0.52 * BOARD_RADIUS)
TRIPLE_OUTER = int(0.58 * BOARD_RADIUS)
DOUBLE_INNER = int(0.85 * BOARD_RADIUS)
DOUBLE_OUTER = int(0.92 * BOARD_RADIUS)

POWER_MAX_TIME = 1.8  # seconds to reach full power
MIN_INACCURACY = 6
MAX_INACCURACY = 30

SECTOR_ORDER = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17,
                3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
BG = (24, 24, 28)
DARK_GRAY = (40, 40, 40)
RED = (200, 40, 40)
GREEN = (30, 140, 40)
YELLOW = (230, 200, 0)
LIGHT = (200, 200, 200)
GOLD = (230, 200, 70)


# -- Scoring / board helpers --
def angle_to_sector(angle: float) -> Tuple[int, int]:
    # Convert angle (atan2 dy,dx) to sector number
    t = -angle - math.pi / 2
    t = t % (2 * math.pi)
    sector_idx = int(t / (2 * math.pi) * 20) % 20
    return SECTOR_ORDER[sector_idx], sector_idx


def score_from_pos(x: float, y: float) -> Tuple[int, int, str]:
    cx, cy = BOARD_CENTER
    dx = x - cx
    dy = y - cy
    r = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    if r <= BULL_INNER_RADIUS:
        return 50, 1, "Bullseye (50)"
    if r <= BULL_OUTER_RADIUS:
        return 25, 1, "Outer Bull (25)"
    if r > DOUBLE_OUTER:
        return 0, 1, "Miss (0)"
    base, idx = angle_to_sector(angle)
    if TRIPLE_INNER <= r <= TRIPLE_OUTER:
        return base * 3, 3, f"Triple {base} ({base*3})"
    if DOUBLE_INNER <= r <= DOUBLE_OUTER:
        return base * 2, 2, f"Double {base} ({base*2})"
    return base, 1, f"Single {base} ({base})"


def draw_board(surface: pygame.Surface):
    cx, cy = BOARD_CENTER
    pygame.draw.circle(surface, BLACK, (cx, cy), BOARD_RADIUS)
    pygame.draw.circle(surface, DARK_GRAY, (cx, cy), DOUBLE_OUTER)
    pygame.draw.circle(surface, BG, (cx, cy), DOUBLE_INNER)
    pygame.draw.circle(surface, DARK_GRAY, (cx, cy), TRIPLE_OUTER)
    pygame.draw.circle(surface, BG, (cx, cy), TRIPLE_INNER)
    pygame.draw.circle(surface, RED, (cx, cy), BULL_INNER_RADIUS)
    pygame.draw.circle(surface, GREEN, (cx, cy), BULL_OUTER_RADIUS, 3)

    for i in range(20):
        a1 = -math.pi/2 + (i) * (2*math.pi/20)
        a2 = -math.pi/2 + (i+1) * (2*math.pi/20)
        outer_color = (20, 20, 20) if i % 2 == 0 else (60, 60, 60)
        inner_color = (60, 10, 10) if i % 2 == 0 else (10, 60, 10)

        pygame.draw.polygon(surface, outer_color, [
            (cx + DOUBLE_INNER * math.cos(a1), cy + DOUBLE_INNER * math.sin(a1)),
            (cx + DOUBLE_OUTER * math.cos(a1), cy + DOUBLE_OUTER * math.sin(a1)),
            (cx + DOUBLE_OUTER * math.cos(a2), cy + DOUBLE_OUTER * math.sin(a2)),
            (cx + DOUBLE_INNER * math.cos(a2), cy + DOUBLE_INNER * math.sin(a2))
        ])
        pygame.draw.polygon(surface, inner_color, [
            (cx + TRIPLE_INNER * math.cos(a1), cy + TRIPLE_INNER * math.sin(a1)),
            (cx + TRIPLE_OUTER * math.cos(a1), cy + TRIPLE_OUTER * math.sin(a1)),
            (cx + TRIPLE_OUTER * math.cos(a2), cy + TRIPLE_OUTER * math.sin(a2)),
            (cx + TRIPLE_INNER * math.cos(a2), cy + TRIPLE_INNER * math.sin(a2))
        ])

    font = pygame.font.SysFont(None, 22, bold=True)
    radius_for_numbers = int(DOUBLE_OUTER * 1.03)
    for i, num in enumerate(SECTOR_ORDER):
        ang = -math.pi/2 + (i + 0.5) * (2*math.pi/20)
        tx = cx + radius_for_numbers * math.cos(ang)
        ty = cy + radius_for_numbers * math.sin(ang)
        text = font.render(str(num), True, LIGHT)
        rect = text.get_rect(center=(tx, ty))
        surface.blit(text, rect)


def draw_power_bar(surface: pygame.Surface, power_ratio: float, pos: Tuple[int, int]):
    x, y = pos
    w, h = 220, 18
    pygame.draw.rect(surface, DARK_GRAY, (x, y, w, h))
    inner_w = int(power_ratio * w)
    pygame.draw.rect(surface, RED, (x, y, inner_w, h))
    pygame.draw.rect(surface, LIGHT, (x, y, w, h), 2)


# -- Data classes --
@dataclass
class Player:
    name: str
    score: int
    throws: List[Tuple[float, float, int, int, str]] = field(default_factory=list)  # (x,y,val,mult,desc)
    turn_start_score: int = 0


# -- Game class --
class DartsMultiplayer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Darts - Multiplayer (Hotseat)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 26)
        self.big_font = pygame.font.SysFont(None, 44, bold=True)
        self.small_font = pygame.font.SysFont(None, 20)

        # start screen settings
        self.num_players = 2
        self.start_score = 301

        # runtime
        self.players: List[Player] = []
        self.current_idx = 0
        self.darts_this_turn = 0
        self.charging = False
        self.charge_start = 0.0
        self.last_throw_anim = []  # list of (x,y,age_frames)
        self.game_running = False
        self.game_over = False
        self.winner_idx = None
        self.message = ""
        self.max_players = 4

    def reset_players(self):
        self.players = []
        for i in range(self.num_players):
            p = Player(name=f"Player {i+1}", score=self.start_score, throws=[])
            p.turn_start_score = self.start_score
            self.players.append(p)
        self.current_idx = 0
        self.darts_this_turn = 0
        self.game_over = False
        self.winner_idx = None
        self.message = ""

    def start_game(self):
        self.reset_players()
        self.game_running = True

    def end_turn_and_advance(self, busted=False, winner=False):
        if winner:
            self.game_over = True
            self.winner_idx = self.current_idx
            self.message = f"{self.players[self.current_idx].name} WINS!"
            return
        # clear darts this turn, update next player's turn_start_score
        self.darts_this_turn = 0
        # advance to next player that hasn't already won (but we stop when someone wins)
        self.current_idx = (self.current_idx + 1) % len(self.players)
        self.players[self.current_idx].turn_start_score = self.players[self.current_idx].score

    def handle_throw(self, final_x: float, final_y: float):
        val, mult, desc = score_from_pos(final_x, final_y)
        player = self.players[self.current_idx]
        prev_score = player.score
        new_score = prev_score - val
        busted = False
        winner = False
        message = ""
        if new_score < 0:
            busted = True
            player.score = player.turn_start_score
            message = f"BUST! Back to {player.score}"
        elif new_score == 0:
            winner = True
            player.score = 0
            message = f"{player.name} WINS!"
        else:
            player.score = new_score

        # record throw
        player.throws.append((final_x, final_y, val, mult, desc))
        self.last_throw_anim.append([final_x, final_y, 0])

        self.darts_this_turn += 1

        if busted:
            # end turn immediately
            self.end_turn_and_advance(busted=True)
        elif winner:
            self.end_turn_and_advance(winner=True)
        elif self.darts_this_turn >= 3:
            self.end_turn_and_advance()
        else:
            # continue current player's turn
            pass
        return val, mult, desc, busted, winner, message

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r:
                        # restart to start screen
                        self.game_running = False
                        self.game_over = False
                        self.winner_idx = None
                        self.message = ""
                    # start-screen controls
                    if not self.game_running:
                        if event.key == pygame.K_2:
                            self.num_players = 2
                        elif event.key == pygame.K_3:
                            self.num_players = 3
                        elif event.key == pygame.K_4:
                            self.num_players = 4
                        elif event.key == pygame.K_5:
                            # allow 5 to toggle starting score to 501 (alt shortcut)
                            self.start_score = 501 if self.start_score == 301 else 301
                        elif event.key == pygame.K_3:  # duplicate mapping for convenience
                            pass
                        elif event.key == pygame.K_SPACE:
                            self.start_game()

                        # quick toggles: 's' to switch start score
                        if event.key == pygame.K_s:
                            self.start_score = 501 if self.start_score == 301 else 301

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and self.game_running and not self.game_over:
                        self.charging = True
                        self.charge_start = pygame.time.get_ticks() / 1000.0

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.charging and self.game_running and not self.game_over:
                        charge_time = (pygame.time.get_ticks() / 1000.0) - self.charge_start
                        power_ratio = min(1.0, max(0.01, charge_time / POWER_MAX_TIME))
                        intended_r = power_ratio * DOUBLE_OUTER
                        inacc = MAX_INACCURACY - (MAX_INACCURACY - MIN_INACCURACY) * (power_ratio)
                        radial_jitter = random.gauss(0, inacc)
                        angular_jitter = random.gauss(0, math.radians(3 + inacc/4.0))
                        dx = mx - BOARD_CENTER[0]
                        dy = my - BOARD_CENTER[1]
                        aim_angle = math.atan2(dy, dx)
                        final_angle = aim_angle + angular_jitter
                        final_r = max(0, intended_r + radial_jitter)
                        final_x = BOARD_CENTER[0] + final_r * math.cos(final_angle)
                        final_y = BOARD_CENTER[1] + final_r * math.sin(final_angle)
                        val, mult, desc, busted, winner, message = self.handle_throw(final_x, final_y)
                        self.charging = False

            # update animations
            for anim in self.last_throw_anim:
                anim[2] += 1
            self.last_throw_anim = [a for a in self.last_throw_anim if a[2] < FPS * 2.0]

            # draw
            self.screen.fill((30, 30, 40))

            # left HUD panel
            hud_w = 320
            pygame.draw.rect(self.screen, (18, 18, 28), (0, 0, hud_w, WINDOW_HEIGHT))

            # Title and controls
            title = self.big_font.render("Darts - Multiplayer (Hotseat)", True, WHITE)
            self.screen.blit(title, (18, 12))
            small = self.small_font
            self.screen.blit(small.render(f"Players: {self.num_players}   Start: {self.start_score}", True, LIGHT), (18, 64))
            self.screen.blit(small.render("Start keys: 2/3/4 players, S to toggle 301/501, Space to start", True, (190,190,190)), (18, 88))

            if not self.game_running:
                # show start card
                prompt = self.font.render("Press Space to start the game (hotseat).", True, GOLD)
                self.screen.blit(prompt, (18, 140))
                info = [
                    "Controls (in-game):",
                    "- Move mouse to aim",
                    "- Hold LEFT MOUSE to charge; release to throw",
                    "- R to restart to start screen, Esc to quit",
                ]
                for i, line in enumerate(info):
                    self.screen.blit(self.small_font.render(line, True, (200,200,200)), (18, 180 + i*22))
                pygame.display.flip()
                continue

            # show players' scores
            for i, p in enumerate(self.players):
                y = 140 + i * 70
                highlight = (80, 50, 18) if i == self.current_idx and not self.game_over else (0,0,0)
                pygame.draw.rect(self.screen, highlight, (18, y-10, hud_w-36, 60))
                name_s = self.font.render(p.name, True, WHITE)
                self.screen.blit(name_s, (26, y))
                score_s = self.big_font.render(str(p.score), True, LIGHT)
                self.screen.blit(score_s, (26, y+28))
                # last throw for that player
                if p.throws:
                    _, _, last_val, last_mult, last_desc = p.throws[-1]
                    last_s = self.small_font.render(f"Last: {last_desc} -> {last_val}", True, (200,200,200))
                    self.screen.blit(last_s, (160, y+4))

            # draw dartboard
            draw_board(self.screen)

            # draw last throws
            for p in self.players:
                for x, y, _, _, _ in p.throws[-6:]:
                    pygame.draw.circle(self.screen, GOLD, (int(x), int(y)), 6)

            for x, y, age in self.last_throw_anim:
                alpha = max(0, 255 - int(age * (255 / (FPS * 1.6))))
                surf = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 235, 120, alpha), (10, 10), 8)
                self.screen.blit(surf, (x - 10, y - 10))

            # crosshair at mouse
            pygame.draw.line(self.screen, (180,180,180), (mx-10, my), (mx+10, my), 1)
            pygame.draw.line(self.screen, (180,180,180), (mx, my-10), (mx, my+10), 1)
            # aim line
            pygame.draw.line(self.screen, (100,100,150), (BOARD_CENTER[0], BOARD_CENTER[1]), (mx, my), 1)

            # HUD right-side: current player info
            cur = self.players[self.current_idx]
            info_x = 18
            info_y = WINDOW_HEIGHT - 160
            pygame.draw.rect(self.screen, (20,20,28), (info_x-8, info_y-8, hud_w-20, 140))
            self.screen.blit(self.font.render(f"Current: {cur.name}", True, WHITE), (info_x, info_y))
            self.screen.blit(self.font.render(f"Score: {cur.score}", True, LIGHT), (info_x, info_y+30))
            self.screen.blit(self.font.render(f"Darts this turn: {self.darts_this_turn}/3", True, LIGHT), (info_x, info_y+60))
            self.screen.blit(self.small_font.render("Hold LMB to charge, release to throw", True, (200,200,200)), (info_x, info_y+92))

            # show power bar while charging
            if self.charging and not self.game_over:
                charge_time = (pygame.time.get_ticks() / 1000.0) - self.charge_start
                power_ratio = min(1.0, max(0.0, charge_time / POWER_MAX_TIME))
                draw_power_bar(self.screen, power_ratio, (26, WINDOW_HEIGHT - 40))
            else:
                draw_power_bar(self.screen, 0.0, (26, WINDOW_HEIGHT - 40))

            # winner overlay
            if self.game_over and self.winner_idx is not None:
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                self.screen.blit(overlay, (0, 0))
                win_txt = self.big_font.render(self.message, True, (240,240,240))
                rect = win_txt.get_rect(center=(WINDOW_WIDTH//2 + 120, WINDOW_HEIGHT//2 - 20))
                self.screen.blit(win_txt, rect)
                hint = self.font.render("Press R to restart to start screen or Esc to quit", True, (200,200,200))
                hrect = hint.get_rect(center=(WINDOW_WIDTH//2 + 120, WINDOW_HEIGHT//2 + 40))
                self.screen.blit(hint, hrect)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


def main():
    gm = DartsMultiplayer()
    gm.run()


if __name__ == "__main__":
    main()