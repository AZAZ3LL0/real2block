"""All PDF texts, keyed by language."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from blockfold.domain.skin.geometry import PartId

Lang = Literal["ru", "en"]

_STRINGS: Mapping[Lang, Mapping[str, str]] = MappingProxyType(
    {
        "ru": MappingProxyType(
            {
                "doc.title": "Blockfold — бумажная фигурка",
                "page.net": "Развёртка: {parts} — стр. {page}",
                "ruler": "50 мм",
                "part.head": "голова",
                "part.body": "туловище",
                "part.right_arm": "правая рука",
                "part.left_arm": "левая рука",
                "part.right_leg": "правая нога",
                "part.left_leg": "левая нога",
            }
        ),
        "en": MappingProxyType(
            {
                "doc.title": "Blockfold — paper figure",
                "page.net": "Net: {parts} — page {page}",
                "ruler": "50 mm",
                "part.head": "head",
                "part.body": "body",
                "part.right_arm": "right arm",
                "part.left_arm": "left arm",
                "part.right_leg": "right leg",
                "part.left_leg": "left leg",
            }
        ),
    }
)


def text(lang: Lang, key: str, **params: object) -> str:
    """Localized string with `str.format` parameters."""
    return _STRINGS[lang][key].format(**params)


def part_name(lang: Lang, part: PartId) -> str:
    """Localized body part name."""
    return text(lang, f"part.{part}")
