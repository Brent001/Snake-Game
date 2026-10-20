"""Fast, headless checks for core static game data."""
from collections import deque

from game.data.active_skill_tree import SKILL_ADJ, SKILL_NODES
from game.data.classes import CLASSES
from game.data.skills import SKILLS


def test_each_class_has_expected_skill_nodes():
    for class_id in CLASSES:
        nodes = [node_id for node_id in SKILL_NODES if node_id.startswith(f"{class_id}:")]
        assert len(nodes) == 336, f"Unexpected skill-node count for {class_id}: {len(nodes)}"


def test_each_skill_lane_is_connected_to_its_root():
    for class_id in CLASSES:
        class_nodes = {
            node_id for node_id in SKILL_NODES if node_id.startswith(f"{class_id}:")
        }
        for skill in SKILLS:
            line_id = skill[0]
            root_id = f"{class_id}:{line_id}:root"
            assert root_id in SKILL_ADJ, f"Missing root {root_id}"

            visited = {root_id}
            queue = deque([root_id])
            while queue:
                current = queue.popleft()
                for neighbour in SKILL_ADJ[current]:
                    if neighbour.startswith(f"{class_id}:") and neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)

            lane_nodes = {
                node_id for node_id in class_nodes
                if SKILL_NODES[node_id].get("line") == line_id
            }
            assert lane_nodes <= visited, (
                f"Disconnected nodes for {class_id}/{line_id}: {sorted(lane_nodes - visited)[:5]}"
            )


def test_game_settings_module_loads_without_gui():
    from game.settings import DEFAULT_SETTINGS, load_settings

    settings = load_settings()
    assert set(settings) == set(DEFAULT_SETTINGS)
    assert 0.0 <= settings["master_volume"] <= 1.0
    assert settings["fps_cap"] in (0, 30, 60, 90, 120)
