"""Single entry point for decoding untrusted images (tech.md §8.2)."""

import io
import warnings

import numpy as np
from PIL import Image

from blockfold.domain.errors import BlockfoldError, InvalidSkinError, UnsupportedFormatError
from blockfold.domain.skin.geometry import LEGACY_HEIGHT, SKIN_SIZE
from blockfold.domain.skin.skin import Pixels

MAX_IMAGE_PIXELS = 40_000_000
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SKIN_SIZES = frozenset({(SKIN_SIZE, SKIN_SIZE), (SKIN_SIZE, LEGACY_HEIGHT)})

_DECODE_ERRORS = (
    OSError,
    SyntaxError,
    ValueError,
    EOFError,
    Image.DecompressionBombError,
    Image.DecompressionBombWarning,
)


def configure_pillow() -> None:
    """Apply process-wide decompression bomb protection; called once at startup."""
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def load_skin_png(data: bytes, sizes: frozenset[tuple[int, int]] = SKIN_SIZES) -> Pixels:
    """Decode a skin PNG to an RGBA array after checking magic bytes and header size."""
    if not data.startswith(PNG_MAGIC):
        raise UnsupportedFormatError("not a PNG")
    try:
        with Image.open(io.BytesIO(data), formats=["PNG"]) as img:
            if img.size not in sizes:
                raise InvalidSkinError(f"unexpected size {img.size}")
            if getattr(img, "is_animated", False):
                raise InvalidSkinError("animated PNG")
            rgba = img.convert("RGBA")
    except BlockfoldError:
        raise
    except _DECODE_ERRORS as exc:
        raise InvalidSkinError("cannot decode PNG") from exc
    return np.asarray(rgba, dtype=np.uint8).copy()
