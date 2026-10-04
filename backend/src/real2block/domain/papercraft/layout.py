"""Page geometry and placement of nets on printable pages (tech.md §4.3)."""

from collections.abc import Mapping, Sequence
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
PART_GAP_MM = 8.0
_EPS_MM = 1e-6


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


def _sorted_by_height(nets: Sequence[NetPart]) -> list[NetPart]:
    # Stable sort: equal heights keep the caller's part order.
    return sorted(nets, key=lambda net: -net.height)


class _Shelves:
    """Shelf packer state for the page being filled."""

    def __init__(self, frame: PageFrame) -> None:
        self.frame = frame
        self.placements: list[Placement] = []
        self.x = frame.content_x
        self.y = frame.content_y
        self.shelf_h = 0.0

    def fits_width(self, net: NetPart) -> bool:
        return self.x + net.width <= self.frame.content_x + self.frame.content_w + _EPS_MM

    def fits_height(self, net: NetPart) -> bool:
        return self.y + net.height <= self.frame.content_y + self.frame.content_h + _EPS_MM

    def new_shelf(self) -> None:
        self.x = self.frame.content_x
        self.y += self.shelf_h + PART_GAP_MM
        self.shelf_h = 0.0

    def place(self, net: NetPart) -> None:
        self.placements.append(Placement(net, self.x, self.y))
        self.x += net.width + PART_GAP_MM
        self.shelf_h = max(self.shelf_h, net.height)


def layout_pages(nets: Sequence[NetPart], paper: Paper) -> tuple[NetPage, ...]:
    """Shelf-pack nets by decreasing height onto pages; parts are never rotated."""
    frame = PageFrame.for_paper(paper)
    pages: list[NetPage] = []
    shelves = _Shelves(frame)
    for net in _sorted_by_height(nets):
        if net.width > frame.content_w + _EPS_MM or net.height > frame.content_h + _EPS_MM:
            raise InvalidOptionsError(f"{net.part} net does not fit on {paper}")
        if shelves.placements and not shelves.fits_width(net):
            shelves.new_shelf()
        if shelves.placements and not shelves.fits_height(net):
            pages.append(NetPage(frame, tuple(shelves.placements)))
            shelves = _Shelves(frame)
        shelves.place(net)
    if shelves.placements:
        pages.append(NetPage(frame, tuple(shelves.placements)))
    return tuple(pages)
