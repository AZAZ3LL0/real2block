"""Single entry point for decoding untrusted images (tech.md §8.2)."""

import io
import warnings
from collections.abc import Callable

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageOps

from real2block.domain.errors import (
    ImageTooLargeError,
    ImageTooSmallError,
    InvalidSkinError,
    Real2blockError,
    UnsupportedFormatError,
)
from real2block.domain.skin.geometry import LEGACY_HEIGHT, SKIN_SIZE
from real2block.domain.skin.skin import Pixels

MAX_IMAGE_PIXELS = 40_000_000
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"
WEBP_TAG_OFFSET = 8
SKIN_SIZES = frozenset({(SKIN_SIZE, SKIN_SIZE), (SKIN_SIZE, LEGACY_HEIGHT)})

PHOTO_MIN_SIDE = 256
PHOTO_MAX_SIDE = 8000
PHOTO_WORK_SIDE = 1024
"""Long side of the decoded photo handed to the analyzer (tech.md §5.2)."""

RgbImage = npt.NDArray[np.uint8]

_DECODE_ERRORS = (
    OSError,
    SyntaxError,
    ValueError,
    EOFError,
)
# The warning is promoted to an error by `configure_pillow`.
_BOMB_ERRORS = (Image.DecompressionBombError, Image.DecompressionBombWarning)


def configure_pillow() -> None:
    """Apply process-wide decompression bomb protection; called once at startup."""
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    warnings.simplefilter("error", Image.DecompressionBombWarning)


def _decode[T](
    data: bytes, fmt: str, on_error: type[Real2blockError], use: Callable[[Image.Image], T]
) -> T:
    """Open `data` as `fmt` and apply `use`; decoder failures become `on_error`.

    Pillow raises the bomb error while reading the header, before any pixel is decoded.
    """
    try:
        with Image.open(io.BytesIO(data), formats=[fmt]) as img:
            return use(img)
    except Real2blockError:
        raise
    except _BOMB_ERRORS as exc:
        raise ImageTooLargeError("decompression bomb") from exc
    except _DECODE_ERRORS as exc:
        raise on_error(f"cannot decode {fmt}") from exc


def load_skin_png(data: bytes, sizes: frozenset[tuple[int, int]] = SKIN_SIZES) -> Pixels:
    """Decode a skin PNG to an RGBA array after checking magic bytes and header size."""
    if not data.startswith(PNG_MAGIC):
        raise UnsupportedFormatError("not a PNG")

    def use(img: Image.Image) -> Pixels:
        if img.size not in sizes:
            raise InvalidSkinError(f"unexpected size {img.size}")
        if getattr(img, "is_animated", False):
            raise InvalidSkinError("animated PNG")
        return np.asarray(img.convert("RGBA"), dtype=np.uint8).copy()

    try:
        return _decode(data, "PNG", InvalidSkinError, use)
    except ImageTooLargeError as exc:
        raise InvalidSkinError("decompression bomb") from exc


def sniff_photo_format(data: bytes) -> str:
    """Pillow format name from magic bytes; the file name and MIME type are never trusted."""
    if data.startswith(JPEG_MAGIC):
        return "JPEG"
    if data.startswith(PNG_MAGIC):
        return "PNG"
    if data.startswith(RIFF_MAGIC) and data[WEBP_TAG_OFFSET:].startswith(WEBP_MAGIC):
        return "WEBP"
    raise UnsupportedFormatError("not a JPEG, PNG or WebP")


def _check_photo_size(width: int, height: int) -> None:
    if max(width, height) > PHOTO_MAX_SIDE:
        raise ImageTooLargeError(f"{width}x{height}")
    if min(width, height) < PHOTO_MIN_SIDE:
        raise ImageTooSmallError(f"{width}x{height}")


def _to_work_rgb(img: Image.Image) -> RgbImage:
    _check_photo_size(*img.size)
    if getattr(img, "is_animated", False):
        raise UnsupportedFormatError("animated image")
    # JPEG can decode at a reduced scale; draft never goes below the requested size.
    img.draft("RGB", (PHOTO_WORK_SIDE, PHOTO_WORK_SIDE))
    upright = ImageOps.exif_transpose(img)
    # Only pixels leave this function, so EXIF and other metadata are dropped here.
    rgb = upright.convert("RGB")
    rgb.thumbnail((PHOTO_WORK_SIDE, PHOTO_WORK_SIDE), Image.Resampling.LANCZOS)
    return np.asarray(rgb, dtype=np.uint8).copy()


def load_photo(data: bytes) -> RgbImage:
    """Decode an uploaded photo to an upright RGB array, long side at most 1024 px."""
    return _decode(data, sniff_photo_format(data), UnsupportedFormatError, _to_work_rgb)
