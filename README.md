# ManicWilly

A playable Jet Set Willy-inspired platformer prototype with:

- Splash screen
- High score table
- Multi-room collectible run
- Animated enemies/backgrounds
- Export workflow for desktop + Android packaging guidance

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/manicwilly_game.py
```

## Controls

- Move: `A/D` or arrows
- Jump: `W`, `UP`, or `SPACE`
- Start game: `ENTER`

## Level/content status

- 12 interconnected rooms in `data/rooms.json`
- 23 collectibles total
- Enemy patrol paths per room
- Completion triggers win screen + persists high score to `data/highscores.json`

## Validation

```bash
python3 src/validate_levels.py
pytest -q
```

## Build / distributables

```bash
./scripts/export_all.sh --check
./scripts/export_all.sh
```

The export script builds a Linux distributable in this environment and documents how to produce Windows/macOS binaries on native runners and Android packages through Buildozer.
