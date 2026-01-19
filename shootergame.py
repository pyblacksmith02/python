"""
PyGame Scrolling Shooter - Simple self-contained game

Controls:
- Arrow keys or WASD to move
- SPACE to shoot
- P to pause
- R to restart after game over
- Esc or window close to quit

Features:
- Smooth movement and framerate-independent updates
- Vertical scrolling starfield background
- Player ship with shooting cooldown and lives
- Multiple enemy types with simple movement patterns
- Enemy bullets, collisions, score, and explosions
- Power-ups (health / rapid-fire)
- Simple level/wave progression
- All graphics drawn with pygame primitives (no external assets)

Run:
    python scroll_shooter.py
"""

import pygame
import random
import math
import sys

# ---- Configuration ----
SCREEN_W = 480
SCREEN_H = 700
FPS = 60

PLAYER_SPEED = 300  # pixels per second
PLAYER_LIVES = 3
PLAYER_FIRE_COOLDOWN = 0.22  # seconds between shots
PLAYER_BULLET_SPEED = -500

ENEMY_BULLET_SPEED = 200
ENEMY_SPAWN_INTERVAL = 1.0  # seconds between spawns (will ramp)
ENEMY_SPEED_MIN = 80
ENEMY_SPEED_MAX = 160

STAR_COUNT = 80

POWERUP_CHANCE = 0.05  # per enemy death

# Colors
WHITE = (255, 255, 255)
BLACK = (8, 8, 12)
RED = (220, 50, 50)
GREEN = (50, 220, 90)
YELLOW = (240, 220, 50)
BLUE = (60, 140, 240)
ORANGE = (255, 140, 40)
GRAY = (120, 120, 130)

# ---- Helper functions ----
def clamp(x, a, b):
    return max(a, min(b, x))

def rect_collide(a, b):
    return a.colliderect(b)

# ---- Game entities ----
class Star:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, SCREEN_W)
        self.y = random.uniform(-SCREEN_H, SCREEN_H)
        self.speed = random.uniform(30, 220)
        self.size = random.choice([1, 1, 2])
        self.color = (180, 180, 255) if self.size == 2 else (160, 160, 200)

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > SCREEN_H:
            self.x = random.uniform(0, SCREEN_W)
            self.y = random.uniform(-20, -5)
            self.speed = random.uniform(30, 220)
            self.size = random.choice([1, 1, 2])

    def draw(self, surf):
        if self.size == 2:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 2)
        else:
            surf.set_at((int(self.x), int(self.y)), self.color)

class Player:
    def __init__(self):
        self.w = 34
        self.h = 42
        self.x = SCREEN_W // 2
        self.y = SCREEN_H - 120
        self.vx = 0
        self.vy = 0
        self.speed = PLAYER_SPEED
        self.lives = PLAYER_LIVES
        self.cooldown = 0.0
        self.respawn_timer = 0.0
        self.invulnerable = 0.0
        self.rapid_fire = False
        self.rapid_fire_time = 0.0

    def rect(self):
        return pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)

    def update(self, dt, keys):
        if self.respawn_timer > 0:
            self.respawn_timer -= dt
            return

        self.vx = 0
        self.vy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vy = 1

        length = math.hypot(self.vx, self.vy)
        if length > 0:
            self.vx /= length
            self.vy /= length

        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt

        # Clamp to screen
        margin = 8
        self.x = clamp(self.x, margin + self.w//2, SCREEN_W - margin - self.w//2)
        self.y = clamp(self.y, margin + self.h//2, SCREEN_H - margin - self.h//2)

        # cooldown
        if self.cooldown > 0:
            self.cooldown -= dt

        # invulnerability
        if self.invulnerable > 0:
            self.invulnerable -= dt

        # rapid fire timer
        if self.rapid_fire:
            self.rapid_fire_time -= dt
            if self.rapid_fire_time <= 0:
                self.rapid_fire = False
                self.cooldown = PLAYER_FIRE_COOLDOWN

    def can_shoot(self):
        cd = PLAYER_FIRE_COOLDOWN * (0.35 if self.rapid_fire else 1.0)
        return self.cooldown <= 0 and self.respawn_timer <= 0

    def shoot(self):
        if not self.can_shoot():
            return None
        self.cooldown = PLAYER_FIRE_COOLDOWN * (0.35 if self.rapid_fire else 1.0)
        # create two slightly offset bullets for nicer feel
        b1 = Bullet(self.x - 8, self.y - self.h//2, 0, PLAYER_BULLET_SPEED, color=YELLOW)
        b2 = Bullet(self.x + 8, self.y - self.h//2, 0, PLAYER_BULLET_SPEED, color=YELLOW)
        return [b1, b2]

    def hit(self):
        if self.invulnerable > 0 or self.respawn_timer > 0:
            return False
        self.lives -= 1
        self.respawn_timer = 1.2
        self.invulnerable = 2.0
        self.x = SCREEN_W // 2
        self.y = SCREEN_H - 120
        return True

    def draw(self, surf):
        # flicker while invulnerable
        visible = True
        if self.invulnerable > 0:
            # flash
            visible = (int(self.invulnerable * 10) % 2) == 0
        if not visible:
            return
        # simple ship: triangle + cockpit
        pts = [(self.x, self.y - self.h//2), (self.x - self.w//2, self.y + self.h//2), (self.x + self.w//2, self.y + self.h//2)]
        pygame.draw.polygon(surf, BLUE, pts)
        pygame.draw.polygon(surf, (20, 20, 70), pts, 2)
        pygame.draw.circle(surf, (200, 220, 255), (int(self.x), int(self.y - 6)), 6)

class Bullet:
    def __init__(self, x, y, vx, vy, color=YELLOW, owner='player'):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.w = 4
        self.h = 8
        self.color = color
        self.owner = owner  # 'player' or 'enemy'

    def rect(self):
        return pygame.Rect(int(self.x - self.w//2), int(self.y - self.h//2), self.w, self.h)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect())

class Enemy:
    def __init__(self, kind=0, x=None):
        # kind 0: basic straight-down
        # kind 1: zig-zag
        # kind 2: shooter (drops then shoots)
        self.kind = kind
        self.w = 32
        self.h = 28
        self.x = random.uniform(40, SCREEN_W - 40) if x is None else x
        self.y = -random.uniform(20, 120)
        self.speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
        self.hp = 1 + kind // 2
        self.shoot_timer = random.uniform(1.0, 2.5) if kind == 2 else None
        self.angle = 0.0
        self.zig_dir = random.choice([-1, 1])
        self.alive = True
        self.point_value = 50 + kind * 25

    def rect(self):
        return pygame.Rect(int(self.x - self.w//2), int(self.y - self.h//2), self.w, self.h)

    def update(self, dt):
        if self.kind == 0:
            self.y += self.speed * dt
        elif self.kind == 1:
            self.y += self.speed * dt
            self.x += math.sin(self.y * 0.02) * 80 * dt
        elif self.kind == 2:
            # slow horizontal drift while moving down
            self.y += (self.speed * 0.6) * dt
            self.x += math.sin(self.y * 0.015) * 60 * dt
            if self.shoot_timer is not None:
                self.shoot_timer -= dt
                if self.shoot_timer <= 0:
                    self.shoot_timer = random.uniform(1.2, 2.5)

        # mark as dead if off-screen bottom
        if self.y > SCREEN_H + 60:
            self.alive = False

    def try_shoot(self):
        # returns a Bullet or None
        if self.kind != 2:
            return None
        if self.shoot_timer is not None and self.shoot_timer <= 0.05:
            # shoot towards the player roughly downwards
            b = Bullet(self.x, self.y + self.h//2, 0, ENEMY_BULLET_SPEED, color=ORANGE, owner='enemy')
            return b
        return None

    def draw(self, surf):
        # enemy body rectangle with kind-based color
        col = (200, 70, 70) if self.kind == 0 else (170, 110, 200) if self.kind == 1 else (80, 200, 100)
        r = self.rect()
        pygame.draw.rect(surf, col, r)
        pygame.draw.rect(surf, (20, 20, 20), r, 2)
        # draw small "eyes"
        pygame.draw.circle(surf, (20,20,20), (int(self.x - 6), int(self.y - 6)), 3)
        pygame.draw.circle(surf, (20,20,20), (int(self.x + 6), int(self.y - 6)), 3)

class Explosion:
    def __init__(self, x, y, duration=0.4):
        self.x = x
        self.y = y
        self.t = 0.0
        self.duration = duration

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        prog = self.t / self.duration
        if prog > 1:
            return
        size = int(8 + prog * 36)
        alpha = int(255 * (1 - prog))
        s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 180, 60, alpha), (size, size), size)
        surf.blit(s, (int(self.x - size), int(self.y - size)), special_flags=pygame.BLEND_PREMULTIPLIED)

    def done(self):
        return self.t >= self.duration

class PowerUp:
    def __init__(self, kind, x, y):
        # kind: 'life' or 'rapid'
        self.kind = kind
        self.x = x
        self.y = y
        self.vy = 80
        self.w = 18
        self.h = 18
        self.active = True

    def rect(self):
        return pygame.Rect(int(self.x - self.w//2), int(self.y - self.h//2), self.w, self.h)

    def update(self, dt):
        self.y += self.vy * dt
        if self.y > SCREEN_H + 30:
            self.active = False

    def draw(self, surf):
        if self.kind == 'life':
            pygame.draw.circle(surf, GREEN, (int(self.x), int(self.y)), 8)
            pygame.draw.circle(surf, (10,10,10), (int(self.x), int(self.y)), 8, 2)
            pygame.draw.rect(surf, (10,10,10), (int(self.x)-2, int(self.y)-6, 4, 12))
            pygame.draw.rect(surf, (10,10,10), (int(self.x)-6, int(self.y)-2, 12, 4))
        elif self.kind == 'rapid':
            pygame.draw.rect(surf, (200,200,70), (int(self.x)-8, int(self.y)-8, 16, 16))
            pygame.draw.polygon(surf, (10,10,10), [(self.x-6,self.y), (self.x-2,self.y-6), (self.x+6,self.y+6)])

# ---- Game ----
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PyGame Scrolling Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 48)
        self.reset()

    def reset(self):
        self.stars = [Star() for _ in range(STAR_COUNT)]
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.enemy_bullets = []
        self.explosions = []
        self.powerups = []
        self.spawn_timer = 0.6
        self.spawn_interval = ENEMY_SPAWN_INTERVAL
        self.score = 0
        self.level = 1
        self.running = True
        self.paused = False
        self.game_over = False
        self.time_elapsed = 0.0

    def spawn_enemy(self):
        # pick kind by level probability
        r = random.random()
        if r < 0.65:
            kind = 0
        elif r < 0.9:
            kind = 1
        else:
            kind = 2
        e = Enemy(kind)
        self.enemies.append(e)

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.time_elapsed += dt

        # background stars
        for s in self.stars:
            s.update(dt)

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        # spawn logic (ramp difficulty over time)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            # ramp spawn faster as level increases/time
            self.spawn_interval = max(0.35, ENEMY_SPAWN_INTERVAL * (0.95 ** (self.level - 1)))
            self.spawn_timer = self.spawn_interval

        # Update enemies
        for e in self.enemies:
            e.update(dt)
            # enemy shooting
            b = e.try_shoot()
            if b is not None:
                self.enemy_bullets.append(b)

        # Update bullets
        for b in self.bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)

        # Update explosions
        for ex in self.explosions:
            ex.update(dt)
        self.explosions = [ex for ex in self.explosions if not ex.done()]

        # Update powerups
        for pu in self.powerups:
            pu.update(dt)
        self.powerups = [p for p in self.powerups if p.active]

        # Collision: player bullets -> enemies
        for b in list(self.bullets):
            if b.owner != 'player':
                continue
            br = b.rect()
            hit_something = False
            for e in list(self.enemies):
                if rect_collide(br, e.rect()):
                    e.hp -= 1
                    if e.hp <= 0:
                        e.alive = False
                        self.score += e.point_value
                        # small chance to drop powerup
                        if random.random() < POWERUP_CHANCE:
                            kind = random.choice(['life', 'rapid'])
                            pu = PowerUp(kind, e.x, e.y)
                            self.powerups.append(pu)
                        self.explosions.append(Explosion(e.x, e.y))
                    hit_something = True
                    break
            if hit_something:
                try:
                    self.bullets.remove(b)
                except ValueError:
                    pass

        # Remove dead enemies and keep within bounds
        self.enemies = [e for e in self.enemies if e.alive]

        # Collision: enemy bullets -> player
        if self.player.respawn_timer <= 0:
            pr = self.player.rect()
            for b in list(self.enemy_bullets):
                if rect_collide(pr, b.rect()):
                    self.enemy_bullets.remove(b)
                    got_hit = self.player.hit()
                    self.explosions.append(Explosion(self.player.x, self.player.y))
                    if self.player.lives < 0:
                        self.game_over = True
                    break

        # Collision: enemies -> player (ramming)
        if self.player.respawn_timer <= 0:
            pr = self.player.rect()
            for e in list(self.enemies):
                if rect_collide(pr, e.rect()):
                    e.alive = False
                    self.explosions.append(Explosion(e.x, e.y))
                    self.explosions.append(Explosion(self.player.x, self.player.y))
                    got_hit = self.player.hit()
                    self.score += 10
                    if self.player.lives < 0:
                        self.game_over = True
                    break

        # Collision: player -> powerups
        pr = self.player.rect()
        for p in list(self.powerups):
            if rect_collide(pr, p.rect()):
                if p.kind == 'life':
                    self.player.lives += 1
                elif p.kind == 'rapid':
                    self.player.rapid_fire = True
                    self.player.rapid_fire_time = 6.0
                p.active = False

        # Clean up bullets off-screen
        self.bullets = [b for b in self.bullets if -40 < b.x < SCREEN_W + 40 and -80 < b.y < SCREEN_H + 80]
        self.enemy_bullets = [b for b in self.enemy_bullets if -40 < b.x < SCREEN_W + 40 and -80 < b.y < SCREEN_H + 80]

        # Progression: increase level every so often by score/time
        if self.score > self.level * 800:
            self.level += 1
            # small reward
            self.player.lives += 1
            # spawn a small wave
            for _ in range(4):
                e = Enemy(kind=random.choice([0,1]), x=random.uniform(40, SCREEN_W-40))
                e.y = -random.uniform(20, 160)
                self.enemies.append(e)

    def handle_input(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p:
                    self.paused = not self.paused
                if ev.key == pygame.K_r and self.game_over:
                    self.reset()
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                # shooting
                if ev.key == pygame.K_SPACE:
                    shots = self.player.shoot()
                    if shots:
                        self.bullets.extend(shots)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:  # allow mouse click to shoot
                    shots = self.player.shoot()
                    if shots:
                        self.bullets.extend(shots)

        # also allow holding space to fire (auto-fire)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            # respect cooldown
            shots = self.player.shoot()
            if shots:
                self.bullets.extend(shots)

    def draw_ui(self, surf):
        # score and lives
        score_s = self.font.render(f"Score: {self.score}", True, WHITE)
        lives_s = self.font.render(f"Lives: {max(0, self.player.lives)}", True, WHITE)
        level_s = self.font.render(f"Level: {self.level}", True, WHITE)
        surf.blit(score_s, (10, 8))
        surf.blit(level_s, (10, 32))
        surf.blit(lives_s, (10, 56))
        # power-up indicator
        if self.player.rapid_fire:
            rf = self.font.render("Rapid: ON", True, (255, 200, 50))
            surf.blit(rf, (SCREEN_W - 110, 8))

    def draw(self):
        # clear
        self.screen.fill(BLACK)

        # stars
        for s in self.stars:
            s.draw(self.screen)

        # draw powerups
        for p in self.powerups:
            p.draw(self.screen)

        # draw enemies
        for e in self.enemies:
            e.draw(self.screen)

        # draw bullets
        for b in self.bullets:
            b.draw(self.screen)
        for b in self.enemy_bullets:
            b.draw(self.screen)

        # draw player
        self.player.draw(self.screen)

        # draw explosions
        for ex in self.explosions:
            ex.draw(self.screen)

        # UI
        self.draw_ui(self.screen)

        # paused / game over overlays
        if self.paused:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,160))
            self.screen.blit(overlay, (0,0))
            txt = self.large_font.render("PAUSED", True, WHITE)
            rect = txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
            self.screen.blit(txt, rect)

        if self.game_over:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            self.screen.blit(overlay, (0,0))
            txt = self.large_font.render("GAME OVER", True, RED)
            rect = txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 20))
            self.screen.blit(txt, rect)
            sub = self.font.render(f"Final Score: {self.score}   Press R to restart", True, WHITE)
            rrect = sub.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 30))
            self.screen.blit(sub, rrect)

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.handle_input(events)

            # update entities
            self.update(dt)

            # drawing
            self.draw()

# ---- Entry point ----
def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()