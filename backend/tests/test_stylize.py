"""Template stylizer (tech.md §4.4, §5.3, §10.5): goldens, determinism, role painting."""

from dataclasses import replace
from typing import get_args

import numpy as np
import pytest

from real2block.api.schemas import SkinSpec
from real2block.domain.color import Rgb, darken
from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, Model, face_rect
from real2block.domain.stylize.base import HAIR_STYLES, HairStyle, Palette
from real2block.domain.stylize.base import SkinSpec as DomainSpec
from real2block.domain.stylize.grids import TEMPLATES_DIR, TemplateError, load_template_dir
from real2block.domain.stylize.roles import SYMBOLS
from real2block.domain.stylize.template import TemplateStylizer, hair_template_name
from tests.helpers import FIXTURES, decode_png

MODELS: tuple[Model, ...] = get_args(Model)
TEMPLATES = load_template_dir(TEMPLATES_DIR)
STYLIZER = TemplateStylizer.from_templates(TEMPLATES)
REFERENCE = SkinSpec.model_validate_json((FIXTURES / "stylize_spec.json").read_text())

# Distinct colors whose shades stay distinct from every base color.
DISTINCT = Palette(
    skin=Rgb(230, 180, 140),
    hair=Rgb(120, 60, 20),
    eye_white=Rgb(250, 250, 250),
    iris=Rgb(20, 90, 200),
    mouth=Rgb(200, 60, 80),
    shirt=Rgb(40, 180, 90),
    pants=Rgb(60, 60, 170),
    shoes=Rgb(150, 150, 30),
)


def spec(style: HairStyle = "short", model: Model = "classic") -> DomainSpec:
    return DomainSpec(model=model, stylizer="template", hair_style=style, palette=DISTINCT)


def reference(style: HairStyle, model: Model) -> DomainSpec:
    return REFERENCE.model_copy(update={"hair_style": style, "model": model}).to_domain()


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("style", HAIR_STYLES)
def test_matches_golden_png(style: HairStyle, model: Model) -> None:
    golden = decode_png((FIXTURES / f"stylize_{style}_{model}.png").read_bytes())
    np.testing.assert_array_equal(STYLIZER.render(reference(style, model)).pixels, golden)


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("style", HAIR_STYLES)
def test_equal_specs_give_equal_bytes(style: HairStyle, model: Model) -> None:
    fresh = TemplateStylizer.from_templates(load_template_dir(TEMPLATES_DIR))
    assert fresh.render(spec(style, model)).to_png() == STYLIZER.render(spec(style, model)).to_png()


def _expected_color(symbol: str) -> Rgb:
    ink = SYMBOLS[symbol]
    base = DISTINCT.of(ink.role)
    return darken(base) if ink.shade else base


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("style", HAIR_STYLES)
def test_every_cell_has_its_role_color(style: HairStyle, model: Model) -> None:
    skin = STYLIZER.render(spec(style, model))
    for part in PART_IDS:
        name = hair_template_name(style) if part == "head" else "outfit_tshirt"
        for face in FACE_IDS:
            rows = TEMPLATES[name].rows(part, face, model)
            rect = face_rect(part, face, model=model)
            for (x, y), symbol in zip(rect.cells(), "".join(rows), strict=True):
                assert skin.rgb_at(x, y) == _expected_color(symbol), (part, face, x, y)


def _base_mask(model: Model) -> np.ndarray:
    mask = np.zeros((64, 64), dtype=bool)
    for part in PART_IDS:
        for face in FACE_IDS:
            rect = face_rect(part, face, model=model)
            mask[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w] = True
    return mask


@pytest.mark.parametrize("model", MODELS)
def test_base_is_opaque_and_everything_else_transparent(model: Model) -> None:
    alpha = STYLIZER.render(spec(model=model)).pixels[..., 3]
    mask = _base_mask(model)
    assert (alpha[mask] == 255).all()
    assert (alpha[~mask] == 0).all()


def test_palette_change_touches_only_that_role() -> None:
    before = STYLIZER.render(spec()).pixels
    recolored = replace(spec(), palette=replace(DISTINCT, shirt=Rgb(255, 0, 0)))
    after = STYLIZER.render(recolored).pixels
    changed = {Rgb(*map(int, px[:3])) for px in before[(before != after).any(axis=2)]}
    assert changed == {DISTINCT.shirt, darken(DISTINCT.shirt)}


def test_hair_style_changes_only_the_head() -> None:
    short = STYLIZER.render(spec("short")).pixels
    long = STYLIZER.render(spec("long")).pixels
    diff = (short != long).any(axis=2)
    head = np.zeros((64, 64), dtype=bool)
    for face in FACE_IDS:
        rect = face_rect("head", face)
        head[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w] = True
    assert diff.any()
    assert not diff[~head].any()


def test_missing_hair_template_is_a_startup_error() -> None:
    partial = {k: v for k, v in TEMPLATES.items() if k != "hair_fringe"}
    with pytest.raises(TemplateError, match=r"hair_fringe\.grid"):
        TemplateStylizer.from_templates(partial)


def test_outfit_must_not_paint_the_head() -> None:
    templates = dict(TEMPLATES)
    templates["outfit_tshirt"] = TEMPLATES["hair_short"]
    with pytest.raises(TemplateError, match="must paint exactly"):
        TemplateStylizer.from_templates(templates)


def test_hair_must_paint_only_the_head() -> None:
    templates = dict(TEMPLATES)
    templates["hair_bald"] = TEMPLATES["outfit_tshirt"]
    with pytest.raises(TemplateError, match="must paint exactly"):
        TemplateStylizer.from_templates(templates)
