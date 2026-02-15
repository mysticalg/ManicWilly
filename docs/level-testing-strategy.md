# Level Testing Strategy

## Automated checks

Run:

```bash
python3 src/validate_levels.py
pytest -q
```

These checks verify:

- Room graph is connected from `start_room`.
- All neighbor references are valid.
- Collectible count remains at useful gameplay scale.

## Manual gameplay checks

- Start at splash and verify ENTER transitions into gameplay.
- Traverse room edges to validate transitions.
- Confirm item pickups update HUD count.
- Confirm enemy collision resets player position.
- Confirm collecting all items writes a score entry to `data/highscores.json`.
