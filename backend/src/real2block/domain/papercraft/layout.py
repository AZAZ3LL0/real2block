"""Page geometry and placement of nets on printable pages (tech.md §4.3)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from real2block.domain.errors import InvalidOptionsError
from real2block.domain.papercraft.net import NetPart

Paper = Literal["A4", "Letter"]

PAPER_SIZES_MM: Mapping[Paper, tuple[float, float]] = MappingProxyType(
    {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}
)
MARGIN_MM = 10.0
HEADER_MM = 12.0
RULER_MM = 50.0


@dataclass(frozen=True, slots=True)
class PageFrame:
    """Paper size and the net area below the header, in millimetres."""

    width: float
    height: float
    content_x: float
    content_y: float
    content_w: float
    content_h: float

    @classmethod
    def for_paper(cls, paper: Paper) -> "PageFrame":
        """Frame for a paper size with fixed margins and header."""
        width, height = PAPER_SIZES_MM[paper]
        return cls(
            width=width,
            height=height,
            content_x=MARGIN_MM,
            content_y=MARGIN_MM + HEADER_MM,
            content_w=width - 2 * MARGIN_MM,
            content_h=height - 2 * MARGIN_MM - HEADER_MM,
        )


@dataclass(frozen=True, slots=True)
class Placement:
    """Net placed on a page; (x, y) is its top-left corner in page millimetres."""

    net: NetPart
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class NetPage:
    """One page of nets."""

    frame: PageFrame
    placements: tuple[Placement, ...]


def place_single(net: NetPart, paper: Paper) -> NetPage:
    """Put one net at the top-left of the content area; rotation is never applied."""
    frame = PageFrame.for_paper(paper)
    if net.width > frame.content_w or net.height > frame.content_h:
        raise InvalidOptionsError(f"{net.part} net does not fit on {paper}")
    return NetPage(frame, (Placement(net, frame.content_x, frame.content_y),))
