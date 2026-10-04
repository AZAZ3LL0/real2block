"""Hostile skin uploads from tech.md §8.2 and §10.8."""

import io
import struct
import zlib

import pytest
from PIL import Image

from real2block.domain.errors import InvalidSkinError, Real2blockError, UnsupportedFormatError
from real2block.domain.vision.loader import PNG_MAGIC, configure_pillow, load_skin_png
from tests.helpers import blank, png_bytes


@pytest.fixture(autouse=True)
def _pillow_guard() -> None:
    configure_pillow()


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _bomb_header(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"\x00" * 1024)
    return PNG_MAGIC + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64)).save(buf, format="JPEG")
    return buf.getvalue()


def _apng() -> bytes:
    buf = io.BytesIO()
    frames = [Image.new("RGBA", (64, 64), (i * 40, 0, 0, 255)) for i in range(2)]
    frames[0].save(buf, format="PNG", save_all=True, append_images=frames[1:])
    return buf.getvalue()


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (_jpeg(), UnsupportedFormatError),
        (b"GIF89a" + b"\x00" * 64, UnsupportedFormatError),
        (png_bytes(blank(63, 64)), InvalidSkinError),
        (png_bytes(blank(64, 48)), InvalidSkinError),
        (_bomb_header(20000, 20000), InvalidSkinError),
        (PNG_MAGIC + b"\x00" * 32, InvalidSkinError),
        (png_bytes(blank())[:60], InvalidSkinError),
        (_apng(), InvalidSkinError),
    ],
    ids=["jpeg", "gif", "63x64", "64x48", "bomb", "garbage", "truncated", "apng"],
)
def test_rejects(data: bytes, error: type[Real2blockError]) -> None:
    with pytest.raises(error):
        load_skin_png(data)


@pytest.mark.parametrize("size", [(64, 64), (64, 32)])
def test_accepts_skin_sizes(size: tuple[int, int]) -> None:
    pixels = load_skin_png(png_bytes(blank(*size)))
    assert pixels.shape == (size[1], size[0], 4)


def test_palette_png_is_converted_to_rgba() -> None:
    buf = io.BytesIO()
    Image.new("P", (64, 64)).save(buf, format="PNG")
    assert load_skin_png(buf.getvalue()).shape == (64, 64, 4)
