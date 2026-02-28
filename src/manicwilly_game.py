from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pygame

WIDTH, HEIGHT = 960, 600
GRAVITY = 1700
PLAYER_SPEED = 290
JUMP_SPEED = 720
ITEM_TARGET_SECONDS = 30 * 60

ROOT = Path(__file__).resolve().parents[1]
ROOMS_FILE = ROOT / "data" / "rooms.json"
SCORE_FILE = ROOT / "data" / "highscores.json"


@dataclass
class Collectible:
    pos: pygame.Vector2
    taken: bool = False


@dataclass
class Stair:
    rect: pygame.Rect
    target: str | None = None
    direction: str | None = None


class Enemy:
    def __init__(self, points: list[list[float]], speed: float):
        self.points = [pygame.Vector2(p) for p in points]
        self.speed = speed
        self.index = 1 if len(self.points) > 1 else 0
        self.pos = self.points[0].copy()

    def update(self, dt: float):
        if len(self.points) < 2:
            return
        target = self.points[self.index]
        delta = target - self.pos
        dist = delta.length()
        if dist < 2:
            self.index = (self.index + 1) % len(self.points)
            return
        self.pos += delta.normalize() * min(self.speed * dt, dist)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.pos.x - 18, self.pos.y - 18, 36, 36)


class Player:
    def __init__(self):
        self.rect = pygame.Rect(40, HEIGHT - 90, 34, 46)
        self.vel_y = 0.0
        self.on_ground = False
        self.on_stairs = False

    def update(self, dt: float, platforms: list[pygame.Rect], walls: list[pygame.Rect], stairs: list[Stair], keys) -> None:
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED * dt
        self.rect.x += int(dx)

        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right

        self.on_stairs = any(self.rect.colliderect(stair.rect) for stair in stairs)
        climbing = self.on_stairs and (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_DOWN] or keys[pygame.K_s])

        if climbing:
            self.vel_y = 0
            climb_speed = PLAYER_SPEED * 0.65
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.rect.y -= int(climb_speed * dt)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.rect.y += int(climb_speed * dt)
        else:
            self.vel_y += GRAVITY * dt
            self.rect.y += int(self.vel_y * dt)

        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p) and self.vel_y >= 0 and self.rect.bottom - p.top < 28:
                self.rect.bottom = p.top
                self.vel_y = 0
                self.on_ground = True
        for wall in walls:
            if self.rect.colliderect(wall):
                if self.vel_y >= 0:
                    self.rect.bottom = wall.top
                    self.vel_y = 0
                    self.on_ground = True
                else:
                    self.rect.top = wall.bottom
                    self.vel_y = 0

        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))
        if self.rect.bottom > HEIGHT - 20:
            self.rect.bottom = HEIGHT - 20
            self.vel_y = 0
            self.on_ground = True
        self.rect.top = max(0, self.rect.top)

    def jump(self):
        if self.on_ground:
            self.vel_y = -JUMP_SPEED


def load_data() -> dict:
    return json.loads(ROOMS_FILE.read_text())


def load_high_scores() -> list[dict]:
    if not SCORE_FILE.exists():
        return []
    return json.loads(SCORE_FILE.read_text())


def save_high_scores(scores: list[dict]) -> None:
    SCORE_FILE.write_text(json.dumps(scores[:10], indent=2))


def build_room(room_cfg: dict):
    platforms = [pygame.Rect(*p) for p in room_cfg["platforms"]]
    walls = [pygame.Rect(*w) for w in room_cfg.get("walls", [])]
    stairs = [Stair(pygame.Rect(*s["rect"]), s.get("target"), s.get("direction")) for s in room_cfg.get("stairs", [])]
    items = [Collectible(pygame.Vector2(c)) for c in room_cfg["collectibles"]]
    enemies = [Enemy(e["path"], e["speed"]) for e in room_cfg["enemies"]]
    return platforms, walls, stairs, items, enemies


def draw_stair(screen: pygame.Surface, stair: Stair) -> None:
    pygame.draw.rect(screen, (140, 90, 50), stair.rect, border_radius=4)
    rung_color = (220, 180, 130)
    for y in range(stair.rect.top + 6, stair.rect.bottom, 10):
        pygame.draw.line(screen, rung_color, (stair.rect.left + 3, y), (stair.rect.right - 3, y), 2)


def draw_player(screen: pygame.Surface, player_rect: pygame.Rect, t: float) -> None:
    pygame.draw.rect(screen, (90, 170, 255), player_rect, border_radius=8)
    head = pygame.Rect(player_rect.x + 7, player_rect.y + 4, 20, 16)
    pygame.draw.ellipse(screen, (248, 222, 190), head)
    eye_y = head.y + 6
    pygame.draw.circle(screen, (40, 40, 40), (head.x + 6, eye_y), 2)
    pygame.draw.circle(screen, (40, 40, 40), (head.x + 14, eye_y), 2)
    step = abs(math.sin(t * 10))
    pygame.draw.rect(screen, (250, 220, 110), (player_rect.x + 4, player_rect.bottom - 8, 10, 6 + int(step * 3)), border_radius=2)
    pygame.draw.rect(screen, (250, 220, 110), (player_rect.right - 14, player_rect.bottom - 8, 10, 6 + int((1 - step) * 3)), border_radius=2)


def draw_enemy(screen: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    pulse = int(120 + 80 * math.sin(t * 8))
    pygame.draw.ellipse(screen, (220, pulse, 120), rect)
    pygame.draw.circle(screen, (30, 30, 30), (rect.centerx - 6, rect.centery - 3), 3)
    pygame.draw.circle(screen, (30, 30, 30), (rect.centerx + 6, rect.centery - 3), 3)
    pygame.draw.arc(screen, (30, 30, 30), (rect.x + 8, rect.y + 11, rect.width - 16, rect.height - 12), math.pi * 0.1, math.pi * 0.9, 2)


def draw_background(screen: pygame.Surface, t: float):
    for y in range(HEIGHT):
        shade = 20 + int(30 * (y / HEIGHT))
        pygame.draw.line(screen, (shade, shade + 8, shade + 22), (0, y), (WIDTH, y))
    for i in range(6):
        x = (i * 180 + math.sin(t + i) * 60) % WIDTH
        pygame.draw.circle(screen, (70, 100, 180), (int(x), 100 + i * 12), 50, 1)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("ManicWilly")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 24)
    tiny = pygame.font.SysFont("consolas", 18)

    data = load_data()
    rooms = data["rooms"]
    room_id = data["start_room"]
    player = Player()

    collected = 0
    total_items = sum(len(r["collectibles"]) for r in rooms.values())
    high_scores = load_high_scores()

    state = "splash"
    elapsed = 0.0

    room_state = {}

    running = True
    while running:
        dt = clock.tick(60) / 1000
        elapsed += dt if state == "playing" else 0
        t = pygame.time.get_ticks() / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "splash" and event.key == pygame.K_RETURN:
                    state = "playing"
                elif state == "playing" and event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    player.jump()
                elif state == "win" and event.key == pygame.K_RETURN:
                    running = False

        draw_background(screen, t)

        if state == "splash":
            title = font.render("MANICWILLY", True, (240, 240, 255))
            subtitle = tiny.render("Jet-set inspired platformer prototype", True, (180, 210, 255))
            prompt = tiny.render("Press ENTER to start", True, (255, 220, 130))
            hs_title = tiny.render("High Scores (fastest full clear):", True, (200, 220, 255))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))
            screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 165))
            screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 210))
            screen.blit(hs_title, (100, 280))
            for idx, s in enumerate(high_scores[:5]):
                line = tiny.render(f"{idx + 1}. {s['seconds']:.1f}s", True, (200, 200, 220))
                screen.blit(line, (120, 310 + idx * 24))

        elif state == "playing":
            if room_id not in room_state:
                room_state[room_id] = build_room(rooms[room_id])
            platforms, walls, stairs, items, enemies = room_state[room_id]

            keys = pygame.key.get_pressed()
            player.update(dt, platforms, walls, stairs, keys)

            for enemy in enemies:
                enemy.update(dt)
                if player.rect.colliderect(enemy.rect()):
                    player.rect.topleft = (40, HEIGHT - 100)
                    player.vel_y = 0

            for item in items:
                if not item.taken and player.rect.colliderect(pygame.Rect(item.pos.x - 10, item.pos.y - 10, 20, 20)):
                    item.taken = True
                    collected += 1

            neighbors = rooms[room_id]["neighbors"]
            if player.rect.left <= 0 and "left" in neighbors:
                room_id = neighbors["left"]
                player.rect.right = WIDTH - 4
            elif player.rect.right >= WIDTH and "right" in neighbors:
                room_id = neighbors["right"]
                player.rect.left = 4
            else:
                for stair in stairs:
                    if stair.target and stair.direction == "up" and player.rect.colliderect(stair.rect) and player.rect.top <= 0:
                        room_id = stair.target
                        player.rect.bottom = HEIGHT - 30
                        break
                    if stair.target and stair.direction == "down" and player.rect.colliderect(stair.rect) and player.rect.bottom >= HEIGHT - 20:
                        room_id = stair.target
                        player.rect.top = 20
                        break

            for p in platforms:
                pygame.draw.rect(screen, (120, 220, 230), p, border_radius=6)
            for w in walls:
                pygame.draw.rect(screen, (95, 125, 165), w, border_radius=5)
            for stair in stairs:
                draw_stair(screen, stair)
            for item in items:
                if not item.taken:
                    pygame.draw.circle(screen, (250, 220, 80), item.pos, 10)
            for enemy in enemies:
                draw_enemy(screen, enemy.rect(), t)

            draw_player(screen, player.rect, t)

            room_text = tiny.render(f"{rooms[room_id]['name']}", True, (230, 230, 255))
            hud = tiny.render(f"Items: {collected}/{total_items}   Time: {elapsed:0.1f}s", True, (255, 255, 255))
            target = tiny.render(f"Target clear time: ~{ITEM_TARGET_SECONDS // 60} minutes", True, (210, 220, 240))
            screen.blit(room_text, (20, 16))
            screen.blit(hud, (20, 40))
            screen.blit(target, (20, 64))

            if collected >= total_items:
                high_scores.append({"seconds": elapsed})
                high_scores = sorted(high_scores, key=lambda v: v["seconds"])[:10]
                save_high_scores(high_scores)
                state = "win"

        elif state == "win":
            done = font.render("All items collected!", True, (255, 240, 180))
            tline = tiny.render(f"Clear time: {elapsed:.1f}s", True, (230, 230, 255))
            replay = tiny.render("Press ENTER to exit.", True, (180, 210, 255))
            screen.blit(done, (WIDTH // 2 - done.get_width() // 2, 220))
            screen.blit(tline, (WIDTH // 2 - tline.get_width() // 2, 265))
            screen.blit(replay, (WIDTH // 2 - replay.get_width() // 2, 300))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
