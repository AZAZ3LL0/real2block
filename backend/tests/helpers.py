import io
import struct
import zlib
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream

FIXTURES = Path(__file__).parent / "fixtures"


def png_bytes(pixels: npt.NDArray[np.uint8]) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="PNG")
    return buf.getvalue()


def decode_png(data: bytes) -> npt.NDArray[np.uint8]:
    """RGBA pixels of a PNG; goldens compare pixels because zlib output varies by build."""
    with Image.open(io.BytesIO(data)) as img:
        return np.asarray(img.convert("RGBA"), dtype=np.uint8)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    crc = struct.pack(">I", zlib.crc32(kind + data))
    return struct.pack(">I", len(data)) + kind + data + crc


def png_header_only(width: int, height: int) -> bytes:
    """Tiny PNG that claims any size in its header: a decompression bomb stand-in."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"\x00" * 1024)
    magic = b"\x89PNG\r\n\x1a\n"
    return magic + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def blank(width: int = 64, height: int = 64) -> npt.NDArray[np.uint8]:
    return np.zeros((height, width, 4), dtype=np.uint8)


PdfSegment = tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True, slots=True)
class StrokeStyle:
    """Stroke state of a drawn segment: width, dash array, alpha state, stroke color."""

    width: float
    dash: tuple[float, ...]
    alpha_state: str | None
    color: tuple[float, ...]


def _point(operands: list[Any]) -> tuple[float, float]:
    return round(float(operands[0]), 2), round(float(operands[1]), 2)


def _segment(a: tuple[float, float], b: tuple[float, float]) -> PdfSegment:
    return (a, b) if a <= b else (b, a)


def _restyle(style: StrokeStyle, op: bytes, operands: list[Any]) -> StrokeStyle:
    match op:
        case b"w":
            return replace(style, width=round(float(operands[0]), 3))
        case b"d":
            return replace(style, dash=tuple(float(v) for v in operands[0]))
        case b"gs":
            return replace(style, alpha_state=str(operands[0]))
        case b"RG":
            return replace(style, color=tuple(round(float(v), 3) for v in operands))
    return style


def pdf_segments(reader: PdfReader, page_index: int) -> Counter[tuple[StrokeStyle, PdfSegment]]:
    """Straight stroked segments of a page with the stroke state they were drawn with."""
    page = reader.pages[page_index]
    style = StrokeStyle(1.0, (), None, (0.0,))
    stack: list[StrokeStyle] = []
    path: list[PdfSegment] = []
    current = (0.0, 0.0)
    out: Counter[tuple[StrokeStyle, PdfSegment]] = Counter()
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        match op:
            case b"q":
                stack.append(style)
            case b"Q":
                style = stack.pop()
            case b"m":
                current = _point(operands)
            case b"l":
                path.append(_segment(current, _point(operands)))
                current = _point(operands)
            case b"S":
                out.update((style, seg) for seg in path)
                path = []
            case b"n":
                path = []
            case _:
                style = _restyle(style, op, operands)
    return out
