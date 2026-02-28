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
        self.pos = pygame.Vector2(self.rect.topleft)
        self.vel_y = 0.0
        self.on_ground = False
        self.on_stairs = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.facing = 1

    def request_jump(self):
        self.jump_buffer_timer = 0.14

    def update(self, dt: float, platforms: list[pygame.Rect], walls: list[pygame.Rect], stairs: list[Stair], keys) -> None:
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED * dt
            self.facing = 1
        self.pos.x += dx
        self.rect.x = int(round(self.pos.x))

        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right

        self.on_stairs = any(self.rect.colliderect(stair.rect) for stair in stairs)
        climbing = self.on_stairs and (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_DOWN] or keys[pygame.K_s])

        can_jump = self.on_ground or self.coyote_timer > 0 or self.on_stairs
        if self.jump_buffer_timer > 0 and can_jump:
            self.vel_y = -JUMP_SPEED
            self.on_stairs = False
            self.jump_buffer_timer = 0.0
            self.coyote_timer = 0.0
            climbing = False

        if climbing:
            self.vel_y = 0
            climb_speed = PLAYER_SPEED * 0.65
            active_stair = next((s for s in stairs if self.rect.colliderect(s.rect)), None)
            if active_stair:
                center_x = active_stair.rect.centerx - self.rect.width // 2
                self.pos.x += (center_x - self.pos.x) * min(1.0, dt * 18)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.pos.y -= climb_speed * dt
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.pos.y += climb_speed * dt
        else:
            self.vel_y += GRAVITY * dt
            self.pos.y += self.vel_y * dt

        self.rect.y = int(round(self.pos.y))

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
        self.pos.x = self.rect.x
        if self.rect.bottom > HEIGHT - 20:
            self.rect.bottom = HEIGHT - 20
            self.vel_y = 0
            self.on_ground = True
        self.rect.top = max(0, self.rect.top)
        self.pos.y = self.rect.y

        if self.on_ground:
            self.coyote_timer = 0.12
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

    def jump(self):
        self.request_jump()


class SpriteBank:
    def __init__(self):
        self.player_walk = self._make_player_walk_frames()
        self.player_climb = self._make_player_climb_frames()
        self.player_jump = self._make_player_jump_frame()
        self.enemy_walk = self._make_enemy_walk_frames()
        self.collectible = self._make_collectible_frames()

    @staticmethod
    def _make_player_walk_frames() -> list[pygame.Surface]:
        frames = []
        for step in (0, 1, 2, 1):
            surf = pygame.Surface((34, 46), pygame.SRCALPHA)
            pygame.draw.rect(surf, (17, 17, 24), (6, 2, 22, 42), width=2, border_radius=4)
            pygame.draw.rect(surf, (58, 124, 235), (9, 19, 16, 17), border_radius=2)
            pygame.draw.rect(surf, (250, 230, 90), (8, 17, 18, 3), border_radius=1)
            pygame.draw.ellipse(surf, (247, 214, 170), (11, 5, 12, 11))
            pygame.draw.rect(surf, (25, 25, 30), (14, 10, 2, 2))
            pygame.draw.rect(surf, (25, 25, 30), (18, 10, 2, 2))
            left_leg = 36 + (2 if step in (0, 2) else 0)
            right_leg = 36 + (2 if step == 1 else 0)
            pygame.draw.rect(surf, (235, 225, 160), (10, left_leg, 5, 7), border_radius=1)
            pygame.draw.rect(surf, (235, 225, 160), (19, right_leg, 5, 7), border_radius=1)
            frames.append(surf)
        return frames

    @staticmethod
    def _make_player_climb_frames() -> list[pygame.Surface]:
        frames = []
        for arm_up in (True, False):
            surf = pygame.Surface((34, 46), pygame.SRCALPHA)
            pygame.draw.rect(surf, (17, 17, 24), (6, 2, 22, 42), width=2, border_radius=4)
            pygame.draw.rect(surf, (58, 124, 235), (9, 19, 16, 17), border_radius=2)
            pygame.draw.ellipse(surf, (247, 214, 170), (11, 5, 12, 11))
            pygame.draw.rect(surf, (235, 225, 160), (10, 36, 5, 7), border_radius=1)
            pygame.draw.rect(surf, (235, 225, 160), (19, 36, 5, 7), border_radius=1)
            if arm_up:
                pygame.draw.rect(surf, (247, 214, 170), (7, 15, 3, 7), border_radius=1)
                pygame.draw.rect(surf, (247, 214, 170), (24, 22, 3, 7), border_radius=1)
            else:
                pygame.draw.rect(surf, (247, 214, 170), (7, 22, 3, 7), border_radius=1)
                pygame.draw.rect(surf, (247, 214, 170), (24, 15, 3, 7), border_radius=1)
            frames.append(surf)
        return frames

    @staticmethod
    def _make_player_jump_frame() -> pygame.Surface:
        surf = pygame.Surface((34, 46), pygame.SRCALPHA)
        pygame.draw.rect(surf, (17, 17, 24), (6, 2, 22, 42), width=2, border_radius=4)
        pygame.draw.rect(surf, (58, 124, 235), (9, 18, 16, 16), border_radius=2)
        pygame.draw.ellipse(surf, (247, 214, 170), (11, 5, 12, 11))
        pygame.draw.rect(surf, (247, 214, 170), (7, 20, 3, 6), border_radius=1)
        pygame.draw.rect(surf, (247, 214, 170), (24, 20, 3, 6), border_radius=1)
        pygame.draw.rect(surf, (235, 225, 160), (11, 34, 5, 6), border_radius=1)
        pygame.draw.rect(surf, (235, 225, 160), (18, 34, 5, 6), border_radius=1)
        return surf

    @staticmethod
    def _make_enemy_walk_frames() -> list[pygame.Surface]:
        frames = []
        for phase in (0, 1, 2, 1):
            surf = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.rect(surf, (28, 32, 40), (4, 7, 28, 18), border_radius=4)
            pygame.draw.rect(surf, (109, 236, 168), (6, 9, 24, 14), border_radius=3)
            pygame.draw.rect(surf, (245, 245, 250), (10, 13, 5, 5), border_radius=1)
            pygame.draw.rect(surf, (245, 245, 250), (21, 13, 5, 5), border_radius=1)
            pygame.draw.rect(surf, (20, 20, 20), (12, 15, 2, 2))
            pygame.draw.rect(surf, (20, 20, 20), (23, 15, 2, 2))
            l = 26 + (phase % 2)
            r = 26 + ((phase + 1) % 2)
            pygame.draw.rect(surf, (228, 112, 78), (10, l, 4, 7), border_radius=1)
            pygame.draw.rect(surf, (228, 112, 78), (22, r, 4, 7), border_radius=1)
            frames.append(surf)
        return frames

    @staticmethod
    def _make_collectible_frames() -> list[pygame.Surface]:
        frames = []
        for size in (8, 9, 10, 9):
            surf = pygame.Surface((20, 20), pygame.SRCALPHA)
            center = 10
            points = [
                (center, center - size),
                (center + size // 2, center - size // 2),
                (center + size, center),
                (center + size // 2, center + size // 2),
                (center, center + size),
                (center - size // 2, center + size // 2),
                (center - size, center),
                (center - size // 2, center - size // 2),
            ]
            pygame.draw.polygon(surf, (255, 228, 95), points)
            pygame.draw.polygon(surf, (255, 249, 200), points, width=1)
            frames.append(surf)
        return frames


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
    pygame.draw.rect(screen, (125, 82, 45), stair.rect, border_radius=3)
    pygame.draw.rect(screen, (64, 43, 26), stair.rect, width=2, border_radius=3)
    rung_color = (230, 196, 150)
    for y in range(stair.rect.top + 6, stair.rect.bottom, 10):
        pygame.draw.line(screen, rung_color, (stair.rect.left + 3, y), (stair.rect.right - 3, y), 2)


def draw_player(screen: pygame.Surface, frame: pygame.Surface, player_rect: pygame.Rect) -> None:
    screen.blit(frame, player_rect.topleft)


def draw_enemy(screen: pygame.Surface, sprites: SpriteBank, rect: pygame.Rect, t: float, enemy: Enemy) -> None:
    frame = sprites.enemy_walk[int((t * 8 + enemy.pos.x * 0.02)) % len(sprites.enemy_walk)]
    screen.blit(frame, (rect.x, rect.y))


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
    sprites = SpriteBank()

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
    stair_transition_cooldown = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000
        stair_transition_cooldown = max(0.0, stair_transition_cooldown - dt)
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
                    player.pos.update(player.rect.topleft)
                    player.vel_y = 0

            for item in items:
                if not item.taken and player.rect.colliderect(pygame.Rect(item.pos.x - 10, item.pos.y - 10, 20, 20)):
                    item.taken = True
                    collected += 1

            neighbors = rooms[room_id]["neighbors"]
            if player.rect.left <= 0 and "left" in neighbors:
                room_id = neighbors["left"]
                player.rect.right = WIDTH - 4
                player.pos.update(player.rect.topleft)
                stair_transition_cooldown = 0.15
            elif player.rect.right >= WIDTH and "right" in neighbors:
                room_id = neighbors["right"]
                player.rect.left = 4
                player.pos.update(player.rect.topleft)
                stair_transition_cooldown = 0.15
            else:
                for stair in stairs:
                    if (
                        stair_transition_cooldown <= 0
                        and stair.target
                        and stair.direction == "up"
                        and player.rect.colliderect(stair.rect)
                        and (keys[pygame.K_UP] or keys[pygame.K_w])
                    ):
                        room_id = stair.target
                        player.rect.bottom = HEIGHT - 28
                        player.rect.x = 54
                        player.pos.update(player.rect.topleft)
                        player.vel_y = 0
                        stair_transition_cooldown = 0.22
                        break
                    if (
                        stair_transition_cooldown <= 0
                        and stair.target
                        and stair.direction == "down"
                        and player.rect.colliderect(stair.rect)
                        and (keys[pygame.K_DOWN] or keys[pygame.K_s])
                    ):
                        room_id = stair.target
                        player.rect.bottom = HEIGHT - 28
                        player.rect.x = WIDTH - 98
                        player.pos.update(player.rect.topleft)
                        player.vel_y = 0
                        stair_transition_cooldown = 0.22
                        break

            for p in platforms:
                pygame.draw.rect(screen, (120, 220, 230), p, border_radius=6)
            for w in walls:
                pygame.draw.rect(screen, (95, 125, 165), w, border_radius=5)
            for stair in stairs:
                draw_stair(screen, stair)
            item_frame = sprites.collectible[int(t * 9) % len(sprites.collectible)]
            for item in items:
                if not item.taken:
                    screen.blit(item_frame, (item.pos.x - 10, item.pos.y - 10))
            for enemy in enemies:
                draw_enemy(screen, sprites, enemy.rect(), t, enemy)

            if player.on_stairs:
                frame = sprites.player_climb[int(t * 8) % len(sprites.player_climb)]
            elif not player.on_ground:
                frame = sprites.player_jump
            else:
                frame = sprites.player_walk[int(t * 10) % len(sprites.player_walk)]

            if player.facing < 0:
                frame = pygame.transform.flip(frame, True, False)
            draw_player(screen, frame, player.rect)

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
