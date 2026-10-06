"""Downsample stylizer: the template skin with the photo face on the head front (tech.md §5.3)."""

import numpy as np

from real2block.domain.errors import InvalidSpecError
from real2block.domain.skin.skin import Skin
from real2block.domain.stylize.base import SkinSpec, Stylizer

OPAQUE = 255


class DownsampleStylizer:
    """Delegates everything but `head.front` to another stylizer."""

    def __init__(self, base: Stylizer) -> None:
        self._base = base

    def render(self, spec: SkinSpec) -> Skin:
        """Base skin with `spec.face_front` painted on the head front, row 0 at the top."""
        if spec.face_front is None:
            raise InvalidSpecError("face_front is required for the downsample stylizer")
        pixels = np.array(
            [[(c.r, c.g, c.b, OPAQUE) for c in row] for row in spec.face_front], dtype=np.uint8
        )
        skin = self._base.render(spec)
        return skin.with_face("head", "front", pixels, model=spec.model)
