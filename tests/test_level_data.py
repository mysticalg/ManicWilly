import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from validate_levels import count_collectibles, load_rooms, validate_graph, validate_stairs


def test_graph_connected_and_valid():
    payload = load_rooms()
    valid, msg = validate_graph(payload)
    assert valid, msg


def test_collectible_count_nontrivial():
    payload = load_rooms()
    assert count_collectibles(payload) >= 20


def test_vertical_links_have_matching_stairs():
    payload = load_rooms()
    valid, msg = validate_stairs(payload)
    assert valid, msg
