"""Downsample stylizer: template skin plus the photo face (tech.md §5.3)."""

from dataclasses import replace
from typing import get_args

import numpy as np
import pytest

from real2block.domain.color import Rgb
from real2block.domain.errors import InvalidSpecError
from real2block.domain.skin.geometry import Model, face_rect
from real2block.domain.stylize.base import Palette, SkinSpec
from real2block.domain.stylize.downsample import DownsampleStylizer
from real2block.domain.stylize.grids import TEMPLATES_DIR, load_template_dir
from real2block.domain.stylize.template import TemplateStylizer

MODELS: tuple[Model, ...] = get_args(Model)
TEMPLATE = TemplateStylizer.from_templates(load_template_dir(TEMPLATES_DIR))
STYLIZER = DownsampleStylizer(TEMPLATE)
PALETTE = Palette(*(Rgb(20 * i, 200 - 20 * i, 100) for i in range(8)))
# Every pixel distinct, so a flipped or shifted face cannot pass.
FACE = tuple(tuple(Rgb(30 * x, 30 * y, 7) for x in range(8)) for y in range(8))


def _spec(model: Model) -> SkinSpec:
    return SkinSpec(
        model=model, stylizer="downsample", hair_style="long", palette=PALETTE, face_front=FACE
    )


@pytest.mark.parametrize("model", MODELS)
def test_head_front_is_the_photo_face(model: Model) -> None:
    front = STYLIZER.render(_spec(model)).face("head", "front", model=model)
    expected = np.array([[(c.r, c.g, c.b, 255) for c in row] for row in FACE], dtype=np.uint8)
    np.testing.assert_array_equal(front, expected)


@pytest.mark.parametrize("model", MODELS)
def test_everything_else_is_the_template_skin(model: Model) -> None:
    spec = _spec(model)
    actual = STYLIZER.render(spec).pixels.copy()
    expected = TEMPLATE.render(replace(spec, stylizer="template")).pixels.copy()
    rect = face_rect("head", "front", "base", model)
    for pixels in (actual, expected):
        pixels[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w] = 0
    np.testing.assert_array_equal(actual, expected)


def test_render_is_byte_stable() -> None:
    assert STYLIZER.render(_spec("classic")).to_png() == STYLIZER.render(_spec("classic")).to_png()


def test_face_front_is_required() -> None:
    with pytest.raises(InvalidSpecError):
        STYLIZER.render(replace(_spec("classic"), face_front=None))
