import re
import string
from typing import get_args

import pytest

from real2block.domain.papercraft.strings import Lang, keys, template

LANGS: tuple[Lang, ...] = get_args(Lang)
CYRILLIC = re.compile("[\u0400-\u04ff]")


def _placeholders(lang: Lang, key: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template(lang, key)) if name}


def test_every_language_has_the_same_keys() -> None:
    assert keys("ru") == keys("en")


@pytest.mark.parametrize("key", sorted(keys("ru")))
def test_placeholders_match_across_languages(key: str) -> None:
    assert _placeholders("ru", key) == _placeholders("en", key)


@pytest.mark.parametrize("key", sorted(keys("en")))
def test_english_strings_have_no_cyrillic(key: str) -> None:
    assert not CYRILLIC.search(template("en", key))


@pytest.mark.parametrize("lang", LANGS)
def test_no_string_is_blank(lang: Lang) -> None:
    assert all(template(lang, key).strip() for key in keys(lang))
