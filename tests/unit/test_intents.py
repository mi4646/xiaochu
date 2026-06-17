"""Intent 枚举测试。"""
import pytest

from apps.chat.intents import Intent


def test_intent_values_are_lowercase_strings():
    for i in Intent:
        assert i.value == i.value.lower()
        assert isinstance(i.value, str)


def test_all_5_intents_exist():
    expected = {"recipe", "recommend", "ingredient", "cooking_qa", "chitchat"}
    assert {i.value for i in Intent} == expected


def test_intent_construction_from_string():
    assert Intent("recipe") is Intent.RECIPE
    assert Intent("chitchat") is Intent.CHITCHAT


def test_invalid_intent_raises():
    with pytest.raises(ValueError):
        Intent("unknown")
