from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pygame

# ── Resolution ─────────────────────────────────────────────────────────────────
# The game renders internally at GAME_W × GAME_H (ZX-Spectrum-scale resolution)
# and is then scaled up 2× to fill the display window.  All physics, collision
# and room data run in the smaller coordinate space which gives chunky "8-bit"
# pixels on screen.

DISPLAY_W, DISPLAY_H = 960, 600   # actual window
GAME_W,    GAME_H    = 480, 300   # internal game canvas
RS = 2                             # room-coordinate scale (rooms.json ÷ RS)

# ── Physics (tuned for GAME_W×GAME_H, slower ZX-Spectrum feel) ─────────────────
GRAVITY      = 380    # px/s²
PLAYER_SPEED = 95     # px/s
JUMP_SPEED   = 240    # px/s  –  height ≈ 240²/(2×380) ≈ 76 px (game) = 152 px (screen)
ITEM_TARGET_SECONDS = 30 * 60

ROOT       = Path(__file__).resolve().parents[1]
ROOMS_FILE = ROOT / "data" / "rooms.json"
SCORE_FILE = ROOT / "data" / "highscores.json"


# ── Procedural ZX-Spectrum-style beeper sounds ─────────────────────────────────

def _square_wave(f0: float, f1: float, duration: float, vol: float = 0.28) -> bytes:
    """Generate a square-wave chirp from frequency f0 to f1 (stereo 16-bit 22050 Hz)."""
    sr = 22050
    n  = int(sr * duration)
    buf = bytearray(n * 4)
    for i in range(n):
        progress = i / max(n - 1, 1)
        freq     = f0 + (f1 - f0) * progress
        half     = sr / max(2.0 * freq, 1.0)
        phase    = i % max(1, int(2 * half))
        raw      = 32767 if phase < half else -32767
        env      = 1.0 - progress * 0.5
        val      = max(-32768, min(32767, int(raw * vol * env)))
        buf[i*4]     = val & 0xFF
        buf[i*4 + 1] = (val >> 8) & 0xFF
        buf[i*4 + 2] = val & 0xFF
        buf[i*4 + 3] = (val >> 8) & 0xFF
    return bytes(buf)


class Sounds:
    """Lazy-initialised beeper sound bank."""

    def __init__(self):
        self._ok = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.jump       = pygame.mixer.Sound(buffer=_square_wave(200,  700, 0.10))
            self.collect    = pygame.mixer.Sound(buffer=_square_wave(700, 1400, 0.07))
            self.die        = pygame.mixer.Sound(buffer=_square_wave(500,   80, 0.22))
            self.transition = pygame.mixer.Sound(buffer=_square_wave(300,  500, 0.06))
            self.win        = pygame.mixer.Sound(buffer=_square_wave(400, 1800, 0.45, 0.32))
            self._ok = True
        except Exception:
            pass  # silently degrade – game works without audio

    def play(self, name: str) -> None:
        if not self._ok:
            return
        snd = getattr(self, name, None)
        if snd:
            snd.play()


# ── Data classes ────────────────────────────────────────────────────────────────

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
        # Scale path from rooms.json coordinates into game space
        self.points = [pygame.Vector2(p[0] / RS, p[1] / RS) for p in points]
        self.speed  = speed / RS
        self.index  = 1 if len(self.points) > 1 else 0
        self.pos    = self.points[0].copy()

    def update(self, dt: float):
        if len(self.points) < 2:
            return
        target = self.points[self.index]
        delta  = target - self.pos
        dist   = delta.length()
        if dist < 1:
            self.index = (self.index + 1) % len(self.points)
            return
        self.pos += delta.normalize() * min(self.speed * dt, dist)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x) - 9, int(self.pos.y) - 9, 18, 18)


# ── Player ──────────────────────────────────────────────────────────────────────

class Player:
    W, H = 17, 23

    def __init__(self):
        self.rect  = pygame.Rect(20, GAME_H - 45, self.W, self.H)
        self.pos   = pygame.Vector2(self.rect.topleft)
        self.vel_y = 0.0
        self.on_ground          = False
        self.on_stairs          = False
        self.coyote_timer       = 0.0
        self.jump_buffer_timer  = 0.0
        # KEY FIX: after jumping we suppress stair-overlap detection for a
        # short window so gravity is not cancelled by the climbing branch.
        self.stair_exit_timer   = 0.0
        self.facing = 1

    def request_jump(self):
        self.jump_buffer_timer = 0.14

    def update(
        self,
        dt: float,
        platforms: list[pygame.Rect],
        walls: list[pygame.Rect],
        stairs: list[Stair],
        keys,
    ) -> None:
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.stair_exit_timer  = max(0.0, self.stair_exit_timer  - dt)

        # ── Horizontal ─────────────────────────────────────────────────────────
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED * dt
            self.facing = 1
        self.pos.x  += dx
        self.rect.x  = int(round(self.pos.x))

        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right

        # ── Stair overlap (suppressed right after a jump) ─────────────────────
        if self.stair_exit_timer <= 0:
            self.on_stairs = any(self.rect.colliderect(s.rect) for s in stairs)
        else:
            self.on_stairs = False

        climbing = self.on_stairs and (
            keys[pygame.K_UP] or keys[pygame.K_w] or
            keys[pygame.K_DOWN] or keys[pygame.K_s]
        )

        # ── Jump ───────────────────────────────────────────────────────────────
        # SPACE / UP / W all trigger jump.  SPACE is the safest on stairs.
        can_jump = self.on_ground or self.coyote_timer > 0 or self.on_stairs
        if self.jump_buffer_timer > 0 and can_jump:
            self.vel_y             = -JUMP_SPEED   # negative = upward in pygame
            self.on_stairs         = False
            self.stair_exit_timer  = 0.35          # stay out of climb mode briefly
            self.jump_buffer_timer = 0.0
            self.coyote_timer      = 0.0
            climbing               = False

        # ── Vertical ───────────────────────────────────────────────────────────
        if climbing:
            self.vel_y   = 0
            climb_speed  = PLAYER_SPEED * 0.65
            active_stair = next(
                (s for s in stairs if self.rect.colliderect(s.rect)), None
            )
            if active_stair:
                # Smoothly centre the player on the ladder/stair
                cx = active_stair.rect.centerx - self.rect.width // 2
                self.pos.x += (cx - self.pos.x) * min(1.0, dt * 18)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.pos.y -= climb_speed * dt
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.pos.y += climb_speed * dt
        else:
            self.vel_y  += GRAVITY * dt
            self.pos.y  += self.vel_y * dt

        self.rect.y = int(round(self.pos.y))

        # ── Ground / wall collision ─────────────────────────────────────────────
        self.on_ground = False
        for p in platforms:
            if (
                self.rect.colliderect(p)
                and self.vel_y >= 0
                and self.rect.bottom - p.top < 14
            ):
                self.rect.bottom = p.top
                self.vel_y       = 0
                self.on_ground   = True
        for wall in walls:
            if self.rect.colliderect(wall):
                if self.vel_y >= 0:
                    self.rect.bottom = wall.top
                    self.vel_y       = 0
                    self.on_ground   = True
                else:
                    self.rect.top = wall.bottom
                    self.vel_y    = 0

        # ── Screen bounds ──────────────────────────────────────────────────────
        self.rect.x = max(0, min(GAME_W - self.rect.width, self.rect.x))
        self.pos.x  = float(self.rect.x)
        if self.rect.bottom > GAME_H - 10:
            self.rect.bottom = GAME_H - 10
            self.vel_y       = 0
            self.on_ground   = True
        self.rect.top = max(0, self.rect.top)
        self.pos.y    = float(self.rect.y)

        # ── Coyote timer ───────────────────────────────────────────────────────
        if self.on_ground:
            self.coyote_timer = 0.12
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

    def jump(self):
        self.request_jump()


# ── Sprite bank (drawn at GAME_W×GAME_H resolution) ────────────────────────────
# Sprites are half the original pixel size; after the 2× upscale they appear
# the same on-screen but each logical pixel becomes a 2×2 block (ZX Spectrum look).

class SpriteBank:
    def __init__(self):
        self.player_walk  = self._player_walk()
        self.player_climb = self._player_climb()
        self.player_jump  = self._player_jump()
        self.enemy_walk   = self._enemy_walk()
        self.collectible  = self._collectible()

    @staticmethod
    def _player_walk() -> list[pygame.Surface]:
        frames = []
        for step in (0, 1, 2, 1):
            s = pygame.Surface((17, 23), pygame.SRCALPHA)
            pygame.draw.rect(s,  (17,  17,  24), (3, 1, 11, 21), width=1, border_radius=2)
            pygame.draw.rect(s,  (58, 124, 235), (4, 9,  9,  9), border_radius=1)
            pygame.draw.rect(s,  (250,230,  90), (4, 8,  9,  2))
            pygame.draw.ellipse(s,(247,214, 170), (5, 2,  7,  6))
            pygame.draw.rect(s,  (25,  25,  30), (7, 4,  1,  1))
            pygame.draw.rect(s,  (25,  25,  30), (10,4,  1,  1))
            ly = 18 + (1 if step in (0, 2) else 0)
            ry = 18 + (1 if step == 1        else 0)
            pygame.draw.rect(s, (235,225,160), (4, ly, 3, 4), border_radius=1)
            pygame.draw.rect(s, (235,225,160), (9, ry, 3, 4), border_radius=1)
            frames.append(s)
        return frames

    @staticmethod
    def _player_climb() -> list[pygame.Surface]:
        frames = []
        for arm_up in (True, False):
            s = pygame.Surface((17, 23), pygame.SRCALPHA)
            pygame.draw.rect(s,  (17,  17,  24), (3, 1, 11, 21), width=1, border_radius=2)
            pygame.draw.rect(s,  (58, 124, 235), (4, 9,  9,  9), border_radius=1)
            pygame.draw.ellipse(s,(247,214, 170), (5, 2,  7,  6))
            pygame.draw.rect(s, (235,225,160), (4, 18, 3, 4), border_radius=1)
            pygame.draw.rect(s, (235,225,160), (9, 18, 3, 4), border_radius=1)
            if arm_up:
                pygame.draw.rect(s,(247,214,170),(3, 7,  2, 4), border_radius=1)
                pygame.draw.rect(s,(247,214,170),(12,10, 2, 4), border_radius=1)
            else:
                pygame.draw.rect(s,(247,214,170),(3, 10, 2, 4), border_radius=1)
                pygame.draw.rect(s,(247,214,170),(12, 7, 2, 4), border_radius=1)
            frames.append(s)
        return frames

    @staticmethod
    def _player_jump() -> pygame.Surface:
        s = pygame.Surface((17, 23), pygame.SRCALPHA)
        pygame.draw.rect(s,  (17,  17,  24), (3, 1, 11, 21), width=1, border_radius=2)
        pygame.draw.rect(s,  (58, 124, 235), (4, 9,  9,  8), border_radius=1)
        pygame.draw.ellipse(s,(247,214, 170), (5, 2,  7,  6))
        pygame.draw.rect(s,  (247,214, 170), (2, 10, 2, 3), border_radius=1)
        pygame.draw.rect(s,  (247,214, 170), (13,10, 2, 3), border_radius=1)
        pygame.draw.rect(s, (235,225,160), (5, 17, 3, 3), border_radius=1)
        pygame.draw.rect(s, (235,225,160), (9, 17, 3, 3), border_radius=1)
        return s

    @staticmethod
    def _enemy_walk() -> list[pygame.Surface]:
        frames = []
        for phase in (0, 1, 2, 1):
            s = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.rect(s,  (28,  32,  40), (2, 3, 14,  9), border_radius=2)
            pygame.draw.rect(s,  (109,236, 168), (3, 4, 12,  7), border_radius=2)
            pygame.draw.rect(s,  (245,245, 250), (5, 6,  3,  3), border_radius=1)
            pygame.draw.rect(s,  (245,245, 250), (10,6,  3,  3), border_radius=1)
            pygame.draw.rect(s,  (20,  20,  20), (6, 7,  1,  1))
            pygame.draw.rect(s,  (20,  20,  20), (11,7,  1,  1))
            l = 13 + (phase % 2)
            r = 13 + ((phase + 1) % 2)
            pygame.draw.rect(s, (228,112, 78), (5, l, 2, 4), border_radius=1)
            pygame.draw.rect(s, (228,112, 78), (11,r, 2, 4), border_radius=1)
            frames.append(s)
        return frames

    @staticmethod
    def _collectible() -> list[pygame.Surface]:
        frames = []
        for size in (4, 5, 5, 4):
            s = pygame.Surface((10, 10), pygame.SRCALPHA)
            c = 5
            pts = [
                (c,       c - size),
                (c + size//2, c - size//2),
                (c + size, c),
                (c + size//2, c + size//2),
                (c,       c + size),
                (c - size//2, c + size//2),
                (c - size, c),
                (c - size//2, c - size//2),
            ]
            pygame.draw.polygon(s, (255, 228,  95), pts)
            pygame.draw.polygon(s, (255, 249, 200), pts, width=1)
            frames.append(s)
        return frames


# ── Persistence ─────────────────────────────────────────────────────────────────

def load_data() -> dict:
    return json.loads(ROOMS_FILE.read_text())


def load_high_scores() -> list[dict]:
    if not SCORE_FILE.exists():
        return []
    return json.loads(SCORE_FILE.read_text())


def save_high_scores(scores: list[dict]) -> None:
    SCORE_FILE.write_text(json.dumps(scores[:10], indent=2))


# ── Room building ───────────────────────────────────────────────────────────────

def _r(xywh: list[int]) -> pygame.Rect:
    """Scale a rooms.json [x,y,w,h] entry into game-space coordinates."""
    return pygame.Rect(
        xywh[0] // RS, xywh[1] // RS,
        max(1, xywh[2] // RS), max(1, xywh[3] // RS),
    )


def build_room(room_cfg: dict):
    platforms  = [_r(p) for p in room_cfg["platforms"]]
    walls      = [_r(w) for w in room_cfg.get("walls", [])]
    stairs     = [
        Stair(_r(s["rect"]), s.get("target"), s.get("direction"))
        for s in room_cfg.get("stairs", [])
    ]
    items      = [Collectible(pygame.Vector2(c[0] / RS, c[1] / RS)) for c in room_cfg["collectibles"]]
    enemies    = [Enemy(e["path"], e["speed"]) for e in room_cfg["enemies"]]
    return platforms, walls, stairs, items, enemies


# ── Drawing helpers ─────────────────────────────────────────────────────────────

def draw_stair(surf: pygame.Surface, stair: Stair) -> None:
    pygame.draw.rect(surf, (125,  82,  45), stair.rect, border_radius=2)
    pygame.draw.rect(surf, ( 64,  43,  26), stair.rect, width=1, border_radius=2)
    for y in range(stair.rect.top + 3, stair.rect.bottom, 5):
        pygame.draw.line(
            surf, (230, 196, 150),
            (stair.rect.left + 2, y), (stair.rect.right - 2, y), 1,
        )


def draw_background(surf: pygame.Surface, t: float) -> None:
    for y in range(GAME_H):
        shade = 20 + int(30 * (y / GAME_H))
        pygame.draw.line(surf, (shade, shade + 8, shade + 22), (0, y), (GAME_W, y))
    for i in range(6):
        x = int((i * 90 + math.sin(t + i) * 30) % GAME_W)
        pygame.draw.circle(surf, (70, 100, 180), (x, 50 + i * 6), 25, 1)


def _fmt_time(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


# ── Stair-transition placement helper ──────────────────────────────────────────

def _place_on_stair(player: Player, target_stairs: list[Stair], from_room: str) -> None:
    """
    After a room transition via stairs, position the player at the floor-level
    base of the matching stair in the target room.

    When arriving via an 'up' stair in the source room we look for the 'down'
    stair in the target room that links back (and vice versa).
    """
    # We don't know the source direction here; we just look for any stair that
    # has target == from_room and place the player near it.
    match = next((s for s in target_stairs if s.target == from_room), None)
    if match:
        player.rect.centerx = match.rect.centerx
        player.rect.bottom  = match.rect.bottom
        # Snap to bottom of stair (should equal floor level)
    else:
        # Fallback: bottom-left
        player.rect.bottom = GAME_H - 14
        player.rect.x      = 20
    player.pos.update(player.rect.topleft)
    player.vel_y      = 0
    player.on_ground  = False


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    pygame.init()
    window    = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
    game_surf = pygame.Surface((GAME_W, GAME_H))
    pygame.display.set_caption("ManicWilly")
    clock   = pygame.time.Clock()
    sprites = SpriteBank()
    sounds  = Sounds()

    # Fonts rendered at game-canvas size → appear 2× larger after upscale
    font  = pygame.font.SysFont("consolas", 12)
    tiny  = pygame.font.SysFont("consolas",  8)
    big   = pygame.font.SysFont("consolas", 14)

    data        = load_data()
    rooms       = data["rooms"]
    room_id     = data["start_room"]
    player      = Player()

    collected   = 0
    total_items = sum(len(r["collectibles"]) for r in rooms.values())
    high_scores = load_high_scores()

    state   = "splash"
    elapsed = 0.0

    room_state: dict = {}
    stair_cooldown   = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000
        stair_cooldown = max(0.0, stair_cooldown - dt)
        if state == "playing":
            elapsed += dt
        t = pygame.time.get_ticks() / 1000

        # ── Events ─────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "splash" and event.key == pygame.K_RETURN:
                    state = "playing"
                elif state == "playing" and event.key in (
                    pygame.K_SPACE, pygame.K_w, pygame.K_UP
                ):
                    player.jump()
                    # Only play jump sound when the buffer is accepted
                elif state == "win" and event.key == pygame.K_RETURN:
                    running = False

        # ── Draw to game canvas ─────────────────────────────────────────────────
        draw_background(game_surf, t)

        # ── Splash ─────────────────────────────────────────────────────────────
        if state == "splash":
            title_s    = big.render("MANICWILLY", True, (240, 240, 255))
            sub_s      = tiny.render("Jet-Set inspired platformer", True, (180, 210, 255))
            prompt_s   = tiny.render("Press ENTER to start", True, (255, 220, 130))
            hs_head_s  = tiny.render("─── HIGH SCORES ───", True, (200, 230, 255))

            game_surf.blit(title_s, (GAME_W // 2 - title_s.get_width() // 2,  48))
            game_surf.blit(sub_s,   (GAME_W // 2 - sub_s.get_width()   // 2,  66))
            game_surf.blit(prompt_s,(GAME_W // 2 - prompt_s.get_width() // 2, 82))
            game_surf.blit(hs_head_s,(GAME_W // 2 - hs_head_s.get_width() // 2, 108))

            if high_scores:
                for idx, sc in enumerate(high_scores[:10]):
                    rank_color = (
                        (255, 215,   0) if idx == 0 else
                        (192, 192, 192) if idx == 1 else
                        (205, 127,  50) if idx == 2 else
                        (200, 210, 230)
                    )
                    line = tiny.render(
                        f"{idx+1:>2}. {_fmt_time(sc['seconds'])}",
                        True, rank_color,
                    )
                    game_surf.blit(line, (GAME_W // 2 - 28, 120 + idx * 10))
            else:
                no_s = tiny.render("No scores yet – be the first!", True, (180, 200, 220))
                game_surf.blit(no_s, (GAME_W // 2 - no_s.get_width() // 2, 122))

        # ── Playing ────────────────────────────────────────────────────────────
        elif state == "playing":
            if room_id not in room_state:
                room_state[room_id] = build_room(rooms[room_id])
            platforms, walls, stairs, items, enemies = room_state[room_id]

            keys = pygame.key.get_pressed()
            player.update(dt, platforms, walls, stairs, keys)

            # Enemy collision → respawn
            for enemy in enemies:
                enemy.update(dt)
                if player.rect.colliderect(enemy.rect()):
                    sounds.play("die")
                    player.rect.topleft = (20, GAME_H - 45)
                    player.pos.update(player.rect.topleft)
                    player.vel_y = 0

            # Collect items
            for item in items:
                if not item.taken:
                    hit = pygame.Rect(
                        int(item.pos.x) - 5, int(item.pos.y) - 5, 10, 10
                    )
                    if player.rect.colliderect(hit):
                        item.taken  = True
                        collected  += 1
                        sounds.play("collect")

            # ── Room transitions ────────────────────────────────────────────────
            neighbors = rooms[room_id]["neighbors"]
            if player.rect.left <= 0 and "left" in neighbors:
                prev_room     = room_id
                room_id       = neighbors["left"]
                player.rect.right = GAME_W - 2
                player.pos.update(player.rect.topleft)
                stair_cooldown = 0.15
                sounds.play("transition")
            elif player.rect.right >= GAME_W and "right" in neighbors:
                prev_room     = room_id
                room_id       = neighbors["right"]
                player.rect.left = 2
                player.pos.update(player.rect.topleft)
                stair_cooldown = 0.15
                sounds.play("transition")
            else:
                for stair in stairs:
                    if stair_cooldown > 0 or not stair.target:
                        continue
                    on_stair = player.rect.colliderect(stair.rect)
                    if not on_stair:
                        continue
                    going_up   = keys[pygame.K_UP] or keys[pygame.K_w]
                    going_down = keys[pygame.K_DOWN] or keys[pygame.K_s]
                    if stair.direction == "up" and going_up:
                        prev_room = room_id
                        room_id   = stair.target
                        if room_id not in room_state:
                            room_state[room_id] = build_room(rooms[room_id])
                        _, _, t_stairs, _, _ = room_state[room_id]
                        _place_on_stair(player, t_stairs, prev_room)
                        stair_cooldown = 0.22
                        sounds.play("transition")
                        break
                    if stair.direction == "down" and going_down:
                        prev_room = room_id
                        room_id   = stair.target
                        if room_id not in room_state:
                            room_state[room_id] = build_room(rooms[room_id])
                        _, _, t_stairs, _, _ = room_state[room_id]
                        _place_on_stair(player, t_stairs, prev_room)
                        stair_cooldown = 0.22
                        sounds.play("transition")
                        break

            # ── Rendering ───────────────────────────────────────────────────────
            for p in platforms:
                pygame.draw.rect(game_surf, (120, 220, 230), p, border_radius=3)
            for w in walls:
                pygame.draw.rect(game_surf, ( 95, 125, 165), w, border_radius=2)
            for stair in stairs:
                draw_stair(game_surf, stair)

            item_frame = sprites.collectible[int(t * 9) % len(sprites.collectible)]
            for item in items:
                if not item.taken:
                    game_surf.blit(
                        item_frame,
                        (int(item.pos.x) - 5, int(item.pos.y) - 5),
                    )

            for enemy in enemies:
                er    = enemy.rect()
                frame = sprites.enemy_walk[int((t * 8 + enemy.pos.x * 0.02)) % 4]
                game_surf.blit(frame, er.topleft)

            # Player sprite selection
            if player.on_stairs:
                frame = sprites.player_climb[int(t * 8) % 2]
            elif not player.on_ground:
                frame = sprites.player_jump
            else:
                frame = sprites.player_walk[int(t * 10) % 4]

            if player.facing < 0:
                frame = pygame.transform.flip(frame, True, False)
            game_surf.blit(frame, player.rect.topleft)

            # ── HUD ─────────────────────────────────────────────────────────────
            room_text = tiny.render(rooms[room_id]["name"], True, (230, 230, 255))
            hud_items = tiny.render(
                f"Items {collected}/{total_items}  Time {_fmt_time(elapsed)}",
                True, (255, 255, 255),
            )
            game_surf.blit(room_text, (6, 6))
            game_surf.blit(hud_items, (6, 16))

            # Best score hint
            if high_scores:
                best = tiny.render(
                    f"Best {_fmt_time(high_scores[0]['seconds'])}",
                    True, (255, 215, 0),
                )
                game_surf.blit(best, (GAME_W - best.get_width() - 4, 6))

            # Win condition
            if collected >= total_items:
                sounds.play("win")
                high_scores.append({"seconds": elapsed})
                high_scores = sorted(high_scores, key=lambda v: v["seconds"])[:10]
                save_high_scores(high_scores)
                state = "win"

        # ── Win ────────────────────────────────────────────────────────────────
        elif state == "win":
            done_s   = font.render("All items collected!", True, (255, 240, 180))
            time_s   = tiny.render(f"Your time: {_fmt_time(elapsed)}", True, (230, 230, 255))
            exit_s   = tiny.render("Press ENTER to exit.", True, (180, 210, 255))
            rank_s   = tiny.render(
                f"Rank #{next((i+1 for i,s in enumerate(high_scores) if s['seconds'] == elapsed), '?')}  "
                f"Best: {_fmt_time(high_scores[0]['seconds'])}",
                True, (255, 215, 0),
            )
            game_surf.blit(done_s, (GAME_W//2 - done_s.get_width()//2, 90))
            game_surf.blit(time_s, (GAME_W//2 - time_s.get_width()//2, 108))
            game_surf.blit(rank_s, (GAME_W//2 - rank_s.get_width()//2, 120))
            game_surf.blit(exit_s, (GAME_W//2 - exit_s.get_width()//2, 135))

        # ── Upscale game canvas → display window (gives the chunky pixel look) ─
        pygame.transform.scale(game_surf, (DISPLAY_W, DISPLAY_H), window)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
