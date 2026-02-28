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


def validate_stairs(payload: dict) -> tuple[bool, str]:
    rooms = payload["rooms"]
    for rid, room in rooms.items():
        stairs = room.get("stairs", [])
        for direction in ("up", "down"):
            if direction in room["neighbors"]:
                matching = [s for s in stairs if s.get("direction") == direction and s.get("target") == room["neighbors"][direction]]
                if not matching:
                    return False, f"room {rid} missing {direction} stair to {room['neighbors'][direction]}"
            else:
                wrong = [s for s in stairs if s.get("direction") == direction]
                if wrong:
                    return False, f"room {rid} has stray {direction} stair"
    return True, "ok"


def simulate_full_clear(payload: dict) -> tuple[bool, str]:
    """Simulate a rules-based full clear across all rooms.

    This does not run pygame physics; it validates that traversal rules exposed
    by the data permit visiting every room and collecting every room item.
    """

    rooms = payload["rooms"]
    start = payload["start_room"]
    if start not in rooms:
        return False, "start_room missing"

    def stair_target(room: dict, direction: str) -> str | None:
        for stair in room.get("stairs", []):
            if stair.get("direction") == direction:
                return stair.get("target")
        return None

    visited: set[str] = set()
    collected = 0
    stack = [start]
    while stack:
        rid = stack.pop()
        if rid in visited:
            continue
        visited.add(rid)
        room = rooms[rid]
        collected += len(room["collectibles"])

        neighbors = room["neighbors"]
        for direction in ("left", "right"):
            nxt = neighbors.get(direction)
            if nxt and nxt not in visited:
                stack.append(nxt)

        for direction in ("up", "down"):
            nxt = neighbors.get(direction)
            if not nxt:
                continue
            if stair_target(room, direction) != nxt:
                return False, f"room {rid} cannot traverse {direction} to {nxt}"
            if nxt not in visited:
                stack.append(nxt)

    if len(visited) != len(rooms):
        return False, f"full-clear traversal reached {len(visited)} / {len(rooms)} rooms"

    expected = count_collectibles(payload)
    if collected != expected:
        return False, f"full-clear collected {collected} / {expected} items"

    return True, "ok"


def validate_unique_room_layouts(payload: dict) -> tuple[bool, str]:
    rooms = payload["rooms"]
    seen: dict[tuple, str] = {}
    for rid, room in rooms.items():
        signature = (
            tuple(tuple(p) for p in room.get("platforms", [])),
            tuple(tuple(w) for w in room.get("walls", [])),
            tuple((s.get("direction"), tuple(s.get("rect", []))) for s in room.get("stairs", [])),
        )
        if signature in seen:
            return False, f"rooms {seen[signature]} and {rid} share identical layout"
        seen[signature] = rid
    return True, "ok"


if __name__ == "__main__":
    data = load_rooms()
    valid, msg = validate_graph(data)
    if not valid:
        raise SystemExit(msg)
    valid, msg = validate_stairs(data)
    if not valid:
        raise SystemExit(msg)
    valid, msg = simulate_full_clear(data)
    if not valid:
        raise SystemExit(msg)
    valid, msg = validate_unique_room_layouts(data)
    if not valid:
        raise SystemExit(msg)
    print(f"rooms={len(data['rooms'])} collectibles={count_collectibles(data)} status=ok")
