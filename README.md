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

The local export script builds a Linux distributable in this environment.

GitHub Actions now builds distributables for:

- Windows (`ManicWilly.exe` zipped artifact)
- macOS (tar.gz artifact)
- Android (debug `.apk` from Buildozer)

Run the **Build distributables** workflow from the Actions tab (or on PR/push) and download artifacts from the workflow run.
