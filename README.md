# ManicWilly

A Jet Set Willy tribute platformer — pure HTML5, zero dependencies. Open `index.html` in any browser and play instantly.

## How to play

Just open `index.html` in a browser. No install, no build step required.

## Controls

| Key | Action |
|-----|--------|
| `←` `→` / `A` `D` | Move left / right |
| `Space` / `↑` / `W` | Jump |
| `↑` / `↓` on a ladder | Climb up / down |
| `Space` / `Enter` | Start / restart |

## The Map — 20 Rooms across 5 Floors

```
ROW 0 (ROOF)    : The Roof → The Tree → The Conservatory
ROW 1 (UPPER)   : The Master Bedroom → The Landing → The Trophy Room
ROW 2 (MAIN)    : The Bathroom → The Bedroom → The Ballroom → The Wine Cellar
ROW 3 (KITCHEN) : The Kitchen → The Kitchen West → The Back Passage → The Wine Store
ROW 4 (BASEMENT): The Cellar → The Crypt → The Caverns
ROW 5 (DEEP)    : The Ship → The Engine Room → The Deep Caverns
```

Rooms connect horizontally (walk off screen edge) and vertically (use ladders marked in yellow).

## Room themes & guardians

| Room | Enemy type |
|------|-----------|
| The Roof / The Tree | Birds |
| The Conservatory | Butterflies |
| The Master Bedroom / The Landing / The Trophy Room | Guardians |
| The Bathroom | Maria (woman protecting the toilet) + Guardians |
| The Bedroom / The Ballroom | Guardians |
| The Wine Cellar / The Wine Store | Bottles |
| The Kitchen | Spoons + Blenders |
| The Kitchen West | Forks + Spoons + Blenders |
| The Back Passage | Guardians |
| The Cellar | Ghosts |
| The Crypt | Skeletons + Ghosts |
| The Caverns / The Deep Caverns | Bats |
| The Ship | Waves |
| The Engine Room | Gears |

## Features

- **20 interconnected rooms** across 5 vertical floors
- **Diagonal staircases** — JSW-style step platforms wind through each room
- **Ladders** — yellow rungs connect floors; press Up/Down to climb
- **13 themed enemy sprites** — pixel-art guardians unique to each area
- **Maria** — the bathroom guardian protecting her toilet (slow but determined)
- **Flashing collectibles** — gather every item in all 20 rooms to win
- **5 lives** — touch any guardian and lose a life; run out and it's Game Over
- **ZX Spectrum aesthetic** — 256×192 native resolution, scaled 3× with CRT scanline overlay
- **Score tracker** — 100 points per item; items/total shown in HUD

## Technical notes

- Single self-contained HTML file (~1300 lines of vanilla JS)
- Native ZX Spectrum resolution (256×192) rendered to an off-screen canvas, scaled 3× to display
- CRT scanline overlay for authenticity
- Sprite data stored as 16-bit row bitmaps per ZX Spectrum attribute cell convention
