"""Papercraft document model and the skin-to-PDF use case."""

from dataclasses import dataclass
from typing import Literal, Protocol

from real2block.domain.errors import WarningCode
from real2block.domain.papercraft.instructions import Cover, Step, build_cover, build_steps
from real2block.domain.papercraft.layout import NetPage, PageFrame, Paper, layout_pages
from real2block.domain.papercraft.net import build_net_part
from real2block.domain.papercraft.strings import Lang
from real2block.domain.skin.geometry import PART_IDS
from real2block.domain.skin.io import ModelChoice, load_print_skin, resolve_model

PrintMode = Literal["color", "numbered"]


@dataclass(frozen=True, slots=True)
class PrintOptions:
    """Domain copy of papercraft options, free of API types."""

    model: ModelChoice
    paper: Paper
    pixel_mm: float
    mode: PrintMode
    flatten_overlay: bool
    grid_lines: bool
    lang: Lang


@dataclass(frozen=True, slots=True)
class PapercraftDocument:
    """Everything the renderer needs; it computes no geometry itself."""

    frame: PageFrame
    cover: Cover
    pages: tuple[NetPage, ...]
    steps: tuple[Step, ...]
    lang: Lang
    grid_lines: bool


@dataclass(frozen=True, slots=True)
class PapercraftResult:
    """Rendered PDF and generation warnings."""

    pdf: bytes
    warnings: tuple[WarningCode, ...]


class DocumentRenderer(Protocol):
    """Turns a document model into PDF bytes."""

    def render(self, document: PapercraftDocument) -> bytes:
        """Render the document."""
        ...


class PapercraftService:
    """Builds the papercraft PDF from an uploaded 64x64 skin."""

    def __init__(self, renderer: DocumentRenderer) -> None:
        self._renderer = renderer

    def build(self, skin_png: bytes, options: PrintOptions) -> PapercraftResult:
        """Validate the skin, prepare its pixels and render the whole PDF."""
        skin = load_print_skin(skin_png)
        model = resolve_model(skin, options.model)
        if options.flatten_overlay:
            skin = skin.flatten_overlay(model)
        filled = skin.fill_transparent_base(model)
        warnings: tuple[WarningCode, ...] = ("TRANSPARENT_BASE_PIXELS",) if filled.filled else ()
        nets = [build_net_part(filled.skin, p, model, options.pixel_mm) for p in PART_IDS]
        document = PapercraftDocument(
            frame=PageFrame.for_paper(options.paper),
            cover=build_cover(filled.skin, model, options.pixel_mm),
            pages=layout_pages(nets, options.paper),
            steps=build_steps(model),
            lang=options.lang,
            grid_lines=options.grid_lines,
        )
        return PapercraftResult(self._renderer.render(document), warnings)
