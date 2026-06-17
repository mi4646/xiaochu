"""recipe handler 的 _parse_json_array 容错测试。"""
import pytest

from apps.recipe.handler import _parse_json_array


def test_clean_json_array():
    out = _parse_json_array('[{"a": 1}]')
    assert out == [{"a": 1}]


def test_with_markdown_json_fence():
    text = '```json\n[{"a": 1}]\n```'
    assert _parse_json_array(text) == [{"a": 1}]


def test_with_plain_markdown_fence():
    text = '```\n[{"a": 1}]\n```'
    assert _parse_json_array(text) == [{"a": 1}]


def test_with_leading_explanation_text():
    text = '当然可以！这是您的菜谱：\n[{"a": 1}]\n希望您喜欢。'
    assert _parse_json_array(text) == [{"a": 1}]


def test_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_json_array("not json at all")


def test_with_surrounding_whitespace():
    assert _parse_json_array('   [{"a": 1}]   \n') == [{"a": 1}]
