"""Photo uploads from tech.md §5.2 step 1, §8.2 and §10.8, including hostile files."""

import io
import tracemalloc

import numpy as np
import pytest
from PIL import Image

from real2block.domain.errors import (
    ImageTooLargeError,
    ImageTooSmallError,
    Real2blockError,
    UnsupportedFormatError,
)
from real2block.domain.vision.loader import configure_pillow, load_photo
from tests.helpers import png_header_only

RED = (220, 30, 30)
BLUE = (30, 30, 220)
EXIF_ORIENTATION = 0x0112
ROTATE_90_CW = 6


@pytest.fixture(autouse=True)
def _pillow_guard() -> None:
    configure_pillow()


def encode(img: Image.Image, fmt: str, **params: object) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **params)
    return buf.getvalue()


def photo(width: int = 400, height: int = 300, mode: str = "RGB") -> Image.Image:
    return Image.new(mode, (width, height), RED if mode == "RGB" else 128)


def animated(fmt: str) -> bytes:
    frames = [Image.new("RGB", (300, 300), color) for color in (RED, BLUE)]
    return encode(frames[0], fmt, save_all=True, append_images=frames[1:])


# accepted input


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_accepts_photo_formats(fmt: str) -> None:
    pixels = load_photo(encode(photo(), fmt))
    assert pixels.shape == (300, 400, 3)
    assert pixels.dtype == np.uint8


@pytest.mark.parametrize("mode", ["RGBA", "L", "P", "CMYK"])
def test_converts_any_mode_to_rgb(mode: str) -> None:
    fmt = "JPEG" if mode == "CMYK" else "PNG"
    assert load_photo(encode(photo(mode=mode), fmt)).shape == (300, 400, 3)


@pytest.mark.parametrize(
    ("size", "expected"),
    [((4000, 3000), (768, 1024)), ((1500, 2500), (1024, 614)), ((1024, 256), (256, 1024))],
)
def test_long_side_is_reduced_to_1024(size: tuple[int, int], expected: tuple[int, int]) -> None:
    pixels = load_photo(encode(photo(*size), "JPEG"))
    assert pixels.shape[:2] == pytest.approx(expected, abs=1)


def test_small_photo_is_not_upscaled() -> None:
    assert load_photo(encode(photo(256, 256), "PNG")).shape == (256, 256, 3)


def test_exif_orientation_is_applied() -> None:
    img = photo(400, 300)
    img.paste(BLUE, (0, 0, 100, 100))
    exif = Image.Exif()
    exif[EXIF_ORIENTATION] = ROTATE_90_CW
    pixels = load_photo(encode(img, "PNG", exif=exif))
    # Rotating 90 degrees clockwise moves the top-left marker to the top-right.
    assert pixels.shape == (400, 300, 3)
    assert tuple(pixels[10, 290]) == BLUE
    assert tuple(pixels[10, 10]) == RED


def test_format_comes_from_magic_bytes_not_extension() -> None:
    # A PNG uploaded as photo.jpg is still read as PNG; the name never reaches the loader.
    assert load_photo(encode(photo(), "PNG")).shape == (300, 400, 3)


# rejected input


@pytest.mark.parametrize(
    "data",
    [
        encode(photo(), "GIF"),
        encode(photo(), "BMP"),
        encode(photo(), "TIFF"),
        b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 64,
        b"%PDF-1.7" + b"\x00" * 64,
        b"",
    ],
    ids=["gif", "bmp", "tiff", "riff-wave", "pdf", "empty"],
)
def test_rejects_other_formats(data: bytes) -> None:
    with pytest.raises(UnsupportedFormatError):
        load_photo(data)


@pytest.mark.parametrize("fmt", ["GIF", "PNG", "WEBP"])
def test_rejects_animated(fmt: str) -> None:
    with pytest.raises(UnsupportedFormatError):
        load_photo(animated(fmt))


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (encode(photo(255, 400), "PNG"), ImageTooSmallError),
        (encode(photo(400, 255), "JPEG"), ImageTooSmallError),
        (png_header_only(8001, 300), ImageTooLargeError),
        (png_header_only(300, 8001), ImageTooLargeError),
        (png_header_only(20000, 20000), ImageTooLargeError),
        # Within the side limit but over MAX_IMAGE_PIXELS.
        (png_header_only(7000, 7000), ImageTooLargeError),
        (png_header_only(255, 9000), ImageTooLargeError),
    ],
    ids=["narrow", "short", "wide", "tall", "bomb", "over-pixel-limit", "both"],
)
def test_rejects_bad_dimensions(data: bytes, error: type[Real2blockError]) -> None:
    with pytest.raises(error):
        load_photo(data)


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_rejects_truncated(fmt: str) -> None:
    data = encode(Image.effect_noise((400, 300), 64).convert("RGB"), fmt)
    with pytest.raises(UnsupportedFormatError):
        load_photo(data[: len(data) // 2])


def test_rejects_garbage_after_magic() -> None:
    with pytest.raises(UnsupportedFormatError):
        load_photo(b"\xff\xd8\xff\xe0" + b"\x00" * 200)


def test_hostile_files_do_not_grow_memory() -> None:
    hostile = [png_header_only(20000, 20000), png_header_only(7000, 7000), animated("WEBP")]
    tracemalloc.start()
    try:
        for _ in range(3):
            for data in hostile:
                with pytest.raises(Real2blockError):
                    load_photo(data)
        baseline, _ = tracemalloc.get_traced_memory()
        for _ in range(50):
            for data in hostile:
                with pytest.raises(Real2blockError):
                    load_photo(data)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert current - baseline < 256 * 1024
    # A decoded 20000x20000 bomb would need over a gigabyte.
    assert peak < 16 * 1024 * 1024
