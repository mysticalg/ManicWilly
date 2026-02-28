import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from validate_levels import (
    count_collectibles,
    load_rooms,
    simulate_full_clear,
    validate_graph,
    validate_stairs,
    validate_unique_room_layouts,
)


def test_graph_connected_and_valid():
    payload = load_rooms()
    valid, msg = validate_graph(payload)
    assert valid, msg


def test_collectible_count_nontrivial():
    payload = load_rooms()
    assert count_collectibles(payload) >= 20


def test_full_game_has_large_room_count():
    payload = load_rooms()
    assert len(payload["rooms"]) >= 50


def test_vertical_links_have_matching_stairs():
    payload = load_rooms()
    valid, msg = validate_stairs(payload)
    assert valid, msg


def test_all_levels_are_traversable_and_game_is_completable():
    payload = load_rooms()
    valid, msg = simulate_full_clear(payload)
    assert valid, msg


def test_every_room_has_a_unique_layout_puzzle():
    payload = load_rooms()
    valid, msg = validate_unique_room_layouts(payload)
    assert valid, msg
