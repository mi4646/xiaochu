"""recommend handler 的 _parse_json 容错测试。"""
import pytest

from apps.recommend.handler import _parse_json


def test_clean_json_object():
    assert _parse_json('{"dishes": ["A"], "desired_count": 3}') == {
        "dishes": ["A"],
        "desired_count": 3,
    }


def test_with_markdown_fence():
    text = '```json\n{"dishes": ["A"], "desired_count": 2}\n```'
    assert _parse_json(text) == {"dishes": ["A"], "desired_count": 2}


def test_with_explanation_text():
    text = '推荐如下：{"dishes": ["A"], "desired_count": 1}'
    assert _parse_json(text) == {"dishes": ["A"], "desired_count": 1}


def test_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_json("nothing here")
