"""All PDF texts, keyed by language."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from real2block.domain.skin.geometry import PartId

Lang = Literal["ru", "en"]

_STRINGS: Mapping[Lang, Mapping[str, str]] = MappingProxyType(
    {
        "ru": MappingProxyType(
            {
                "doc.title": "real2block — бумажная фигурка",
                "page.net": "Развёртка: {parts} — стр. {page}",
                "ruler": "50 мм",
                "cover.title": "Бумажная фигурка",
                "cover.front": "Спереди",
                "cover.back": "Сзади",
                "cover.size": "Размер готовой фигурки: {width} × {height} × {depth} мм "
                "(ширина × высота × глубина)",
                "cover.parts": "Детали",
                "cover.part": "{name} — метки {code}-A…{code}-G",
                "cover.tools": "Понадобится",
                "tool.scissors": "ножницы",
                "tool.glue": "клей-карандаш",
                "tool.ruler": "линейка",
                "tool.scoring": "тупой нож для биговки",
                "print.title": "Как печатать и резать",
                "print.scale": "Печатайте в масштабе 100% («Фактический размер»), "
                "без подгонки под страницу.",
                "print.check": "Проверьте линейку: отрезок ниже должен быть ровно 50 мм. "
                "Если нет — исправьте настройки печати и напечатайте снова.",
                "print.legend": "Линии",
                "line.cut": "сплошная — резать",
                "line.fold": "пунктир — согнуть внутрь",
                "line.tab": "штриховка — клапан, на него наносится клей",
                "print.labels": "Клапан с меткой, например H-A, приклеивается под ребро "
                "с той же меткой.",
                "print.score.title": "Биговка",
                "print.score": "Перед сгибом проведите тупым ножом по линейке вдоль каждого "
                "пунктира, не прорезая бумагу. Так сгиб получится ровным.",
                "print.cut": "Вырезайте по сплошной линии вместе с клапанами.",
                "steps.title": "Сборка",
                "step.label": "Шаг {index}. {title}",
                "step.cut.title": "Вырежьте детали",
                "step.cut.body": "Вырежьте все детали по сплошным линиям.",
                "step.fold.title": "Согните",
                "step.fold.body": "Согните все пунктирные линии внутрь, рисунком наружу.",
                "step.head.title": "Голова H",
                "step.head.body": "Склейте клапан H-G (боковой шов), затем H-A…H-C (верх), "
                "последними H-D…H-F (низ).",
                "step.body.title": "Туловище B",
                "step.body.body": "Тот же порядок: B-G, затем B-A…B-C, последними B-D…B-F.",
                "step.limbs.title": "Руки и ноги",
                "step.limbs.body": "Руки RA, LA и ноги RL, LL — в том же порядке: G, A…C, D…F.",
                "step.assemble.title": "Соберите фигурку",
                "step.assemble.body": "Ноги приклейте верхними гранями к нижней грани туловища "
                "(правая нога под правую половину). Руки — внутренними боковыми гранями "
                "к боковым граням туловища. Голову — нижней гранью по центру верхней грани "
                "туловища. Зоны склейки выделены рамкой.",
                "legend.title": "Легенда цветов",
                "legend.hint.color": "Сколько клеток каждого цвета в фигурке.",
                "legend.hint.numbered": "Клетки развёрток напечатаны серым с номером цвета: "
                "раскрасьте их по таблице или соберите из цветных блоков.",
                "legend.number": "№",
                "legend.color": "Цвет",
                "legend.hex": "Код",
                "legend.cells": "Клеток",
                "legend.other": "прочие",
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
                "doc.title": "real2block — paper figure",
                "page.net": "Net: {parts} — page {page}",
                "ruler": "50 mm",
                "cover.title": "Paper figure",
                "cover.front": "Front",
                "cover.back": "Back",
                "cover.size": "Finished size: {width} × {height} × {depth} mm "
                "(width × height × depth)",
                "cover.parts": "Parts",
                "cover.part": "{name} — labels {code}-A…{code}-G",
                "cover.tools": "You will need",
                "tool.scissors": "scissors",
                "tool.glue": "glue stick",
                "tool.ruler": "ruler",
                "tool.scoring": "blunt knife for scoring",
                "print.title": "How to print and cut",
                "print.scale": "Print at 100% scale (“Actual size”), with no fit to page.",
                "print.check": "Check the ruler: the line below must be exactly 50 mm. "
                "If it is not, fix the print settings and print again.",
                "print.legend": "Lines",
                "line.cut": "solid — cut",
                "line.fold": "dashed — fold inwards",
                "line.tab": "hatched — glue tab, put glue here",
                "print.labels": "A tab with a label such as H-A is glued under the edge "
                "with the same label.",
                "print.score.title": "Scoring",
                "print.score": "Before folding, run a blunt knife along a ruler over every "
                "dashed line without cutting through. The folds come out straight.",
                "print.cut": "Cut along the solid lines, keeping the tabs.",
                "steps.title": "Assembly",
                "step.label": "Step {index}. {title}",
                "step.cut.title": "Cut out",
                "step.cut.body": "Cut out every part along the solid lines.",
                "step.fold.title": "Fold",
                "step.fold.body": "Fold every dashed line inwards, picture side out.",
                "step.head.title": "Head H",
                "step.head.body": "Glue tab H-G (side seam) first, then H-A…H-C (top), "
                "and H-D…H-F (bottom) last.",
                "step.body.title": "Body B",
                "step.body.body": "Same order: B-G, then B-A…B-C, and B-D…B-F last.",
                "step.limbs.title": "Arms and legs",
                "step.limbs.body": "Arms RA, LA and legs RL, LL in the same order: G, A…C, D…F.",
                "step.assemble.title": "Put it together",
                "step.assemble.body": "Glue the top faces of the legs to the bottom of the body "
                "(right leg under the right half). Glue the inner sides of the arms to the sides "
                "of the body. Glue the bottom of the head to the middle of the top of the body. "
                "Glue zones are framed.",
                "legend.title": "Color legend",
                "legend.hint.color": "How many cells of each color the figure has.",
                "legend.hint.numbered": "Net cells are printed gray with a color number: "
                "color them using this table or build them from colored blocks.",
                "legend.number": "No.",
                "legend.color": "Color",
                "legend.hex": "Hex",
                "legend.cells": "Cells",
                "legend.other": "other",
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


def keys(lang: Lang) -> frozenset[str]:
    """All string keys of a language."""
    return frozenset(_STRINGS[lang])


def template(lang: Lang, key: str) -> str:
    """Raw localized string with its `{name}` placeholders unfilled."""
    return _STRINGS[lang][key]


def text(lang: Lang, key: str, **params: object) -> str:
    """Localized string with `str.format` parameters."""
    return template(lang, key).format(**params)


def part_name(lang: Lang, part: PartId) -> str:
    """Localized body part name."""
    return text(lang, f"part.{part}")
