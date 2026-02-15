from __future__ import annotations

import json
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS_FILE = ROOT / "data" / "rooms.json"


def load_rooms() -> dict:
    payload = json.loads(ROOMS_FILE.read_text())
    return payload


def validate_graph(payload: dict) -> tuple[bool, str]:
    rooms = payload["rooms"]
    start = payload["start_room"]

    if start not in rooms:
        return False, "start_room missing"

    for rid, room in rooms.items():
        for _, nxt in room["neighbors"].items():
            if nxt not in rooms:
                return False, f"room {rid} points to unknown neighbor {nxt}"

    visited = set()
    q = deque([start])
    while q:
        current = q.popleft()
        if current in visited:
            continue
        visited.add(current)
        for nxt in rooms[current]["neighbors"].values():
            if nxt not in visited:
                q.append(nxt)

    if len(visited) != len(rooms):
        return False, f"graph disconnected: visited {len(visited)} of {len(rooms)}"

    return True, "ok"


def count_collectibles(payload: dict) -> int:
    return sum(len(v["collectibles"]) for v in payload["rooms"].values())


if __name__ == "__main__":
    data = load_rooms()
    valid, msg = validate_graph(data)
    if not valid:
        raise SystemExit(msg)
    print(f"rooms={len(data['rooms'])} collectibles={count_collectibles(data)} status=ok")
