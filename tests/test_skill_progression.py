"""Regression tests for close-reach skill bindings and level-gated abilities."""
import pytest

from game.data.keybinds import (
    CLASS_SKILL_PRESETS,
    SKILL_ACTION_METHODS,
    SKILL_SLOT_IDS,
    is_skill_unlocked,
    skill_for_key,
    skill_unlock_level,
    skills_unlocked_at_level,
)
from game.settings import DEFAULT_SKILL_SLOT_KEYS, DEFAULT_SKILL_SET_TOGGLE_KEY, _valid_skill_key


CLASSES = ("viper", "python", "cobra", "mamba")


@pytest.mark.parametrize("class_id", CLASSES)
def test_two_bars_have_five_distinct_slots_and_cover_each_class_skill(class_id):
    bars = CLASS_SKILL_PRESETS[class_id]
    assert len(bars) == 2
    assert all(len(bar) == 5 for bar in bars)
    assert len(set(bars[0] + bars[1])) == 10
    assert set(bars[0] + bars[1]) == set(SKILL_ACTION_METHODS)


@pytest.mark.parametrize("class_id", CLASSES)
def test_slot_keys_resolve_to_each_bar_assignment(class_id):
    slot_keys = dict(DEFAULT_SKILL_SLOT_KEYS)
    for bar_index, bar in enumerate(CLASS_SKILL_PRESETS[class_id]):
        for slot_key, skill_id in zip(SKILL_SLOT_IDS, bar):
            assert skill_for_key(class_id, bar_index, slot_keys, slot_keys[slot_key]) == skill_id
        assert skill_for_key(class_id, bar_index, slot_keys, "w") is None


@pytest.mark.parametrize("class_id", CLASSES)
def test_starter_actions_and_signature_unlock_levels(class_id):
    assert is_skill_unlocked(class_id, "dash", 1)
    assert is_skill_unlocked(class_id, "strike", 1)
    assert not is_skill_unlocked(class_id, "shed", 1)
    assert is_skill_unlocked(class_id, "shed", 2)
    assert not is_skill_unlocked(class_id, "class_skill", 2)
    assert is_skill_unlocked(class_id, "class_skill", 3)


@pytest.mark.parametrize("class_id", CLASSES)
def test_one_new_skill_unlocks_per_level_from_two_through_eleven(class_id):
    for level in range(2, 12):
        unlocked = skills_unlocked_at_level(class_id, level)
        assert len(unlocked) == 1
        assert skill_unlock_level(class_id, unlocked[0]) == level
    assert skills_unlocked_at_level(class_id, 1) == ()
    assert skills_unlocked_at_level(class_id, 12) == ()


def test_default_keys_are_close_reach_unique_and_avoid_reserved_controls():
    slot_keys = list(DEFAULT_SKILL_SLOT_KEYS.values())
    assert slot_keys == ["q", "e", "r", "f", "c"]
    assert len(slot_keys) == len(set(slot_keys))
    assert DEFAULT_SKILL_SET_TOGGLE_KEY == "x"
    assert all(_valid_skill_key(key) for key in slot_keys + [DEFAULT_SKILL_SET_TOGGLE_KEY])
    for key in "wasdpmnk":
        assert not _valid_skill_key(key)
