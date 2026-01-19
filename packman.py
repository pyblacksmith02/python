"""
Pac-Man (Packman) - simple Pygame implementation

Controls:
- Arrow keys or WASD to move Pac-Man.
- R to restart after game over / win.
- Esc or window close to quit.

Features:
- Tile-based map with walls, pellets, and power pellets.
- Smooth movement between tiles.
- Simple ghost AI (basic chase + random choices).
- Power mode: eat power pellet to make ghosts vulnerable for a short time.
- Score, lives, and level progression (same map repeats).
- No sound by default (easy to add).

Note: This is a lightweight educational implementation, not a pixel-perfect recreation.
"""

import pygame
import sys
import random
from collections import deque

# Configuration
TILE_SIZE = 24
FPS = 60
SCREEN_BG = (5, 5, 30)
WALL_COLOR = (33, 33, 150)
PELLET_COLOR = (255, 240, 160)
POWER_PELLET_COLOR = (255, 100, 100)
PACMAN_COLOR = (255, 220, 0)
GHOST_COLORS = [(200, 40, 120), (40, 200, 200), (40, 160, 40), (220, 120, 30)]
VULNERABLE_COLOR = (100, 120, 255)

START_LIVES = 3
POWER_DURATION = 7.0  # seconds ghosts vulnerable
FRIGHT_FLASH_THRESHOLD = 2.0  # seconds: ghosts flash near end

# Map legend:
# '#' wall
# '.' pellet
# 'o' power pellet
# ' ' empty / corridor
# 'P' player start
# 'G' ghost start
MAP = [
"############################",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#o####.#####.##.#####.####o#",
"#.####.#####.##.#####.####.#",
"#..........................#",
"#.####.##.########.##.####.#",
"#.####.##.########.##.####.#",
"#......##....##....##......#",
"######.##### ## #####.######",
"     #.##### ## #####.#     ",
"     #.##          ##.#     ",
"     #.## ###--### ##.#     ",
"######.## #      # ##.######",
"      .   #      #   .      ",
"######.## #      # ##.######",
"     #.## ######## ##.#     ",
"     #.##          ##.#     ",
"     #.## ######## ##.#     ",
"######.## ######## ##.######",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#o..##................##..o#",
"###.##.##.########.##.##.###",
"###.##.##.########.##.##.###",
"#......##....##....##......#",
"#.##########.##.##########.#",
"#.##########.##.##########.#",
"#..........................#",
"############################",
]

# parse map dimensions
MAP_H = len(MAP)
MAP_W = max(len(row) for row in MAP)
SCREEN_W = MAP_W * TILE_SIZE
SCREEN_H = MAP_H * TILE_SIZE

# Helper functions
def grid_to_pixel(gx, gy):
    return gx * TILE_SIZE + TILE_SIZE // 2, gy * TILE_SIZE + TILE_SIZE // 2

def pixel_to_grid(px, py):
    return px // TILE_SIZE, py // TILE_SIZE

def valid_tile(tile):
    x, y = tile
    if x < 0 or x >= MAP_W or y < 0 or y >= MAP_H:
        return False
    return MAP[y][x] != '#'

def neighbors(tile):
    x, y = tile
    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx, ny = x+dx, y+dy
        if 0 <= nx < MAP_W and 0 <= ny < MAP_H and MAP[ny][nx] != '#':
            yield (nx, ny)

def manhattan(a,b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# Simple pathfinder: BFS for shortest path on grid (tile coordinates)
def bfs_shortest(start, goal, blocked=set()):
    if start == goal:
        return [start]
    q = deque([start])
    came = {start: None}
    while q:
        cur = q.popleft()
        for nxt in neighbors(cur):
            if nxt in blocked or nxt in came:
                continue
            came[nxt] = cur
            if nxt == goal:
                path = [goal]
                while cur is not None:
                    path.append(cur)
                    cur = came[cur]
                return list(reversed(path))
            q.append(nxt)
    return None

class Player:
    def __init__(self, pos):
        self.gx, self.gy = pos  # tile grid coordinates (center of tile)
        px, py = grid_to_pixel(self.gx, self.gy)
        self.x, self.y = px, py  # pixel position (center)
        self.dir = (0,0)
        self.next_dir = (0,0)
        self.speed = 100  # pixels per second
        self.radius = TILE_SIZE//2 - 2
        self.alive = True

    def set_direction(self, dx, dy):
        self.next_dir = (dx, dy)

    def update(self, dt):
        # attempt to change direction if possible
        if self.next_dir != self.dir:
            ndx, ndy = self.next_dir
            nx = self.gx + ndx
            ny = self.gy + ndy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and MAP[ny][nx] != '#':
                self.dir = self.next_dir

        dx, dy = self.dir
        if dx == dy == 0:
            return

        move_px = dx * self.speed * dt
        move_py = dy * self.speed * dt
        self.x += move_px
        self.y += move_py

        # center snap when reaching tile center
        target_cx = self.gx * TILE_SIZE + TILE_SIZE // 2
        target_cy = self.gy * TILE_SIZE + TILE_SIZE // 2

        # update grid position once crossing half tile threshold
        new_gx, new_gy = pixel_to_grid(int(self.x), int(self.y))
        # allow positions inside corridors even if not perfectly snapped
        # but prevent walking into walls: if the center tile ahead is a wall, revert movement
        ahead_gx = self.gx + dx
        ahead_gy = self.gy + dy
        if 0 <= ahead_gx < MAP_W and 0 <= ahead_gy < MAP_H and MAP[ahead_gy][ahead_gx] == '#':
            # can't advance into wall: snap back to tile center
            self.x = target_cx
            self.y = target_cy
            self.dir = (0,0)
            self.next_dir = (0,0)
        else:
            # update grid pos if we've moved into a new tile center region
            center_x = self.gx * TILE_SIZE + TILE_SIZE // 2
            center_y = self.gy * TILE_SIZE + TILE_SIZE // 2
            if abs(self.x - center_x) >= TILE_SIZE//2 or abs(self.y - center_y) >= TILE_SIZE//2:
                self.gx, self.gy = new_gx, new_gy
                # wrap tunnels horizontally if present (map uses spaces)
                if self.gx < 0:
                    self.gx = MAP_W - 1
                    self.x = self.gx * TILE_SIZE + TILE_SIZE // 2
                if self.gx >= MAP_W:
                    self.gx = 0
                    self.x = self.gx * TILE_SIZE + TILE_SIZE // 2

    def draw(self, surf):
        pygame.draw.circle(surf, PACMAN_COLOR, (int(self.x), int(self.y)), self.radius)
        # simple mouth to indicate direction
        dx, dy = self.dir
        if dx == dy == 0:
            dx = 1
        angle = 0
        if dx == 1: angle = 0
        elif dx == -1: angle = 180
        elif dy == 1: angle = 90
        elif dy == -1: angle = 270
        # mouth as a triangle
        mouth_len = self.radius
        p1 = (int(self.x), int(self.y))
        import math
        a1 = math.radians(angle - 25)
        a2 = math.radians(angle + 25)
        p2 = (int(self.x + mouth_len * math.cos(a1)), int(self.y + mouth_len * math.sin(a1)))
        p3 = (int(self.x + mouth_len * math.cos(a2)), int(self.y + mouth_len * math.sin(a2)))
        pygame.draw.polygon(surf, SCREEN_BG, [p1,p2,p3])

class Ghost:
    def __init__(self, pos, color, home):
        self.gx, self.gy = pos
        px, py = grid_to_pixel(self.gx, self.gy)
        self.x, self.y = px, py
        self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.speed = 80  # pixels per second (slower than player)
        self.radius = TILE_SIZE//2 - 2
        self.color = color
        self.state = "chase"  # chase, frightened, eaten
        self.fright_timer = 0.0
        self.home = home  # tile to return to after being eaten

    def set_fright(self, duration):
        if self.state != "eaten":
            self.state = "frightened"
            self.fright_timer = duration

    def update(self, dt, player_tile, blocked=set()):
        # decrease fright timer
        if self.state == "frightened":
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                self.state = "chase"

        if self.state == "eaten":
            # head home
            target = self.home
        elif self.state == "frightened":
            # random wandering away from player
            target = None
        else:
            # chase: target player tile
            target = player_tile

        # decide when to change direction: when close to tile centers
        center_x = self.gx * TILE_SIZE + TILE_SIZE // 2
        center_y = self.gy * TILE_SIZE + TILE_SIZE // 2
        reached_center = abs(self.x - center_x) < 2 and abs(self.y - center_y) < 2

        if reached_center:
            # snap to tile center
            self.x = center_x
            self.y = center_y
            # choose new direction
            choices = [d for d in [(1,0),(-1,0),(0,1),(0,-1)]
                       if (self.gx + d[0], self.gy + d[1]) not in blocked and
                       0 <= self.gx + d[0] < MAP_W and 0 <= self.gy + d[1] < MAP_H and
                       MAP[self.gy + d[1]][self.gx + d[0]] != '#']
            # don't reverse unless no other choice
            rev = (-self.dir[0], -self.dir[1])
            nonrev = [d for d in choices if d != rev]
            if nonrev:
                choices = nonrev

            if target is None:
                # frightened / random movement
                if choices:
                    self.dir = random.choice(choices)
            else:
                # pick direction that minimizes distance to target (greedy)
                best = None
                best_dist = 1e9
                for d in choices:
                    nx, ny = self.gx + d[0], self.gy + d[1]
                    dist = manhattan((nx, ny), target)
                    if dist < best_dist:
                        best_dist = dist
                        best = d
                if best:
                    self.dir = best
                elif choices:
                    self.dir = random.choice(choices)

            # update grid position for next movement
            self.gx += self.dir[0]
            self.gy += self.dir[1]

        # move pixels
        self.x += self.dir[0] * self.speed * dt
        self.y += self.dir[1] * self.speed * dt

        # If eaten and reached home tile, revive
        if self.state == "eaten" and (self.gx, self.gy) == self.home:
            self.state = "chase"
            self.speed = 80

    def draw(self, surf):
        col = self.color
        if self.state == "frightened":
            col = VULNERABLE_COLOR
        elif self.state == "eaten":
            col = (120,120,120)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.radius)
        # eyes
        eye_offset = self.radius // 2
        pygame.draw.circle(surf, (255,255,255), (int(self.x - eye_offset/2), int(self.y - 5)), self.radius//3)
        pygame.draw.circle(surf, (255,255,255), (int(self.x + eye_offset/2), int(self.y - 5)), self.radius//3)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Packman - Simple Pac-Man")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.bigfont = pygame.font.SysFont(None, 48)
        self.reset()

    def reset(self):
        # parse map, find start positions
        self.pellets = set()
        self.power_pellets = set()
        self.walls = set()
        player_start = None
        ghost_starts = []
        ghost_home = (MAP_W//2, MAP_H//2)  # center by default

        for y,row in enumerate(MAP):
            for x,ch in enumerate(row):
                if ch == '#':
                    self.walls.add((x,y))
                elif ch == '.':
                    self.pellets.add((x,y))
                elif ch == 'o':
                    self.power_pellets.add((x,y))
                elif ch == 'P':
                    player_start = (x,y)
                elif ch == 'G':
                    ghost_starts.append((x,y))
                elif ch == '-':
                    # treated as walkway, keep empty
                    pass
                elif ch == ' ':
                    pass

        # fallback player start if not specified
        if not player_start:
            player_start = (MAP_W//2, MAP_H-5)
        self.player = Player(player_start)

        # create ghosts (up to 4)
        self.ghosts = []
        # pick default ghost starts if none specified
        if not ghost_starts:
            ghost_starts = [(MAP_W//2-1, MAP_H//2), (MAP_W//2+1, MAP_H//2), (MAP_W//2-3, MAP_H//2), (MAP_W//2+3, MAP_H//2)]
        for i,pos in enumerate(ghost_starts[:4]):
            col = GHOST_COLORS[i % len(GHOST_COLORS)]
            g = Ghost(pos, col, ghost_home)
            self.ghosts.append(g)

        self.score = 0
        self.lives = START_LIVES
        self.level = 1
        self.power_timer = 0.0
        self.game_over = False
        self.win = False
        self.message = ""
        # small delay before player can move so they don't instantly run
        self.start_delay = 0.5

    def toggle_power_mode(self):
        self.power_timer = POWER_DURATION
        for g in self.ghosts:
            if g.state != "eaten":
                g.set_fright(POWER_DURATION)

    def update(self, dt):
        if self.game_over:
            return

        if self.start_delay > 0:
            self.start_delay -= dt
            return

        # player movement
        self.player.update(dt)

        # pellet collection: check player's grid tile
        pgx, pgy = self.player.gx, self.player.gy
        if (pgx, pgy) in self.pellets:
            self.pellets.remove((pgx,pgy))
            self.score += 10
        if (pgx, pgy) in self.power_pellets:
            self.power_pellets.remove((pgx,pgy))
            self.score += 50
            self.toggle_power_mode()

        # update ghosts
        blocked = set(self.walls)
        for g in self.ghosts:
            # don't let ghosts move into pellet-only blocked tiles (they can walk corridors)
            g.update(dt, (self.player.gx, self.player.gy), blocked)

        # power mode handling
        if self.power_timer > 0:
            self.power_timer -= dt
            if self.power_timer <= 0:
                # end power: ensure ghosts revert if not eaten
                for g in self.ghosts:
                    if g.state == "frightened":
                        g.state = "chase"

        # collisions with ghosts
        for g in self.ghosts:
            dist2 = (self.player.x - g.x)**2 + (self.player.y - g.y)**2
            min_dist = (self.player.radius + g.radius) ** 2
            if dist2 <= min_dist:
                if g.state == "frightened":
                    # eat ghost
                    self.score += 200
                    g.state = "eaten"
                    # send ghost to home tile (it will move there)
                    gx, gy = g.home
                    g.gx, g.gy = gx, gy  # snap grid to home to simplify
                    px, py = grid_to_pixel(gx, gy)
                    g.x, g.y = px, py
                    g.speed = 120
                elif g.state == "eaten":
                    # pass through while eaten
                    pass
                else:
                    # ghost kills player
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_over = True
                        self.message = "Game Over"
                    else:
                        # reset positions
                        # reposition player to start
                        # freeze briefly
                        self.player.x, self.player.y = grid_to_pixel(self.player.gx, self.player.gy)
                        self.player.dir = (0,0)
                        self.player.next_dir = (0,0)
                        for gi,gst in enumerate(self.ghosts):
                            # send ghosts back to their start
                            # find a clear tile near center
                            gst.gx, gst.gy = self.ghosts[gi].gx, self.ghosts[gi].gy
                            px, py = grid_to_pixel(gst.gx, gst.gy)
                            gst.x, gst.y = px, py
                        self.start_delay = 0.8
                    break

        # win condition: all pellets and power pellets consumed
        if not self.pellets and not self.power_pellets:
            self.level += 1
            self.score += 500
            self.reset()  # restart same map, more speed perhaps
            for g in self.ghosts:
                g.speed += 5  # slightly increase difficulty
            self.player.speed += 5

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.set_direction(-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.set_direction(1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.set_direction(0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.set_direction(0, 1)

    def draw_map(self, surf):
        # draw walls
        for y,row in enumerate(MAP):
            for x,ch in enumerate(row):
                px = x * TILE_SIZE
                py = y * TILE_SIZE
                if ch == '#':
                    pygame.draw.rect(surf, WALL_COLOR, (px, py, TILE_SIZE, TILE_SIZE))
                # optional: draw decorative corridors for '-' char
                elif ch == '-':
                    pygame.draw.rect(surf, (20,20,60), (px, py, TILE_SIZE, TILE_SIZE))

        # pellets
        for (x,y) in self.pellets:
            cx, cy = grid_to_pixel(x,y)
            pygame.draw.circle(surf, PELLET_COLOR, (cx, cy), 3)
        # power pellets
        for (x,y) in self.power_pellets:
            cx, cy = grid_to_pixel(x,y)
            pygame.draw.circle(surf, POWER_PELLET_COLOR, (cx, cy), 6)

    def draw_hud(self, surf):
        text = self.font.render(f"Score: {self.score}", True, (220,220,220))
        surf.blit(text, (8,8))
        lvl = self.font.render(f"Level: {self.level}", True, (220,220,220))
        surf.blit(lvl, (8,32))
        lives_text = self.font.render(f"Lives: {self.lives}", True, (220,220,220))
        surf.blit(lives_text, (8,56))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_r:
                        self.reset()

            self.handle_input()
            self.update(dt)

            # draw
            self.screen.fill(SCREEN_BG)
            self.draw_map(self.screen)
            for g in self.ghosts:
                g.draw(self.screen)
            self.player.draw(self.screen)
            self.draw_hud(self.screen)

            if self.game_over:
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((0,0,0,180))
                self.screen.blit(overlay, (0,0))
                txt = self.bigfont.render(self.message, True, (240,240,240))
                rect = txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 20))
                self.screen.blit(txt, rect)
                hint = self.font.render("Press R to restart or Esc to quit", True, (200,200,200))
                hrect = hint.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 30))
                self.screen.blit(hint, hrect)

            pygame.display.flip()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()