"""Parser and validator of `.grid` template files (tech.md §4.4).

Templates are loaded once at startup; any defect raises `TemplateError` so the
app refuses to start instead of failing on a request.
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import get_args

from real2block.domain.skin.geometry import FACE_IDS, PART_IDS, FaceId, Model, PartId, face_rect
from real2block.domain.stylize.roles import SYMBOLS, TRANSPARENT_SYMBOL

MODELS: tuple[Model, ...] = get_args(Model)
GRID_SUFFIX = ".grid"
HEADER_PREFIX = "#"
REQUIRED_KEYS = frozenset({"part", "face", "w", "h"})
OPTIONAL_KEYS = frozenset({"model"})
_PAIR_RE = re.compile(r"^([a-z]+)=(\S+)$")
TEMPLATES_DIR = Path(__file__).parent / "templates"
"""Bundled templates shipped with the package."""

BlockKey = tuple[PartId, FaceId, Model | None]


class TemplateError(ValueError):
    """A `.grid` file is malformed or incomplete; the app must not start."""


@dataclass(frozen=True, slots=True)
class GridBlock:
    """Symbols of one face in texture orientation, row-major."""

    part: PartId
    face: FaceId
    model: Model | None
    rows: tuple[str, ...]
    line: int

    @property
    def key(self) -> BlockKey:
        """Identity of the block inside its template."""
        return (self.part, self.face, self.model)


class GridTemplate:
    """Validated template: every face of every part it mentions resolves for both models."""

    __slots__ = ("_blocks", "name")

    def __init__(self, name: str, blocks: Mapping[BlockKey, GridBlock]) -> None:
        self.name = name
        self._blocks = MappingProxyType(dict(blocks))

    @property
    def parts(self) -> frozenset[PartId]:
        """Body parts the template paints."""
        return frozenset(part for part, _, _ in self._blocks)

    def rows(self, part: PartId, face: FaceId, model: Model) -> tuple[str, ...]:
        """Symbols of a face for a model; a model-specific block wins over a shared one."""
        block = self._blocks.get((part, face, model)) or self._blocks.get((part, face, None))
        if block is None:
            raise KeyError(f"{self.name} has no {part}.{face} for {model}")
        return block.rows


@dataclass(frozen=True, slots=True)
class _Spot:
    """Position in a template file, for error messages."""

    name: str
    line: int

    def error(self, message: str) -> TemplateError:
        return TemplateError(f"{self.name}{GRID_SUFFIX}:{self.line}: {message}")

    def below(self, offset: int) -> "_Spot":
        return _Spot(self.name, self.line + offset)


def _header_fields(text: str, at: _Spot) -> dict[str, str]:
    fields: dict[str, str] = {}
    for pair in text.removeprefix(HEADER_PREFIX).split():
        match = _PAIR_RE.match(pair)
        if not match:
            raise at.error(f"expected key=value, got {pair!r}")
        key, value = match.groups()
        if key in fields:
            raise at.error(f"repeated key {key!r}")
        fields[key] = value
    keys = set(fields)
    if not keys >= REQUIRED_KEYS or not keys <= REQUIRED_KEYS | OPTIONAL_KEYS:
        raise at.error(f"header keys must be part, face, w, h and optional model: {text}")
    return fields


def _choice[T: str](value: str, allowed: tuple[T, ...], what: str, at: _Spot) -> T:
    for option in allowed:
        if option == value:
            return option
    raise at.error(f"unknown {what} {value!r}")


def _size(fields: Mapping[str, str], at: _Spot) -> tuple[int, int]:
    try:
        return int(fields["w"]), int(fields["h"])
    except ValueError as exc:
        raise at.error("w and h must be integers") from exc


def _check_size(key: BlockKey, size: tuple[int, int], at: _Spot) -> None:
    # Sizes come from the UV layout; a shared block must fit every model.
    part, face, model = key
    for each in (model,) if model else MODELS:
        rect = face_rect(part, face, model=each)
        if (rect.w, rect.h) != size:
            raise at.error(f"{part}.{face} is {rect.w}x{rect.h} for {each}, header says {size}")


def _check_row(row: str, width: int, at: _Spot) -> None:
    if len(row) != width:
        raise at.error(f"row {row!r} must be {width} symbols wide")
    for symbol in row:
        if symbol == TRANSPARENT_SYMBOL:
            raise at.error("transparent cells are overlay-only; .grid blocks are base")
        if symbol not in SYMBOLS:
            raise at.error(f"unknown symbol {symbol!r}")


def _read_block(lines: list[str], index: int, name: str) -> GridBlock:
    at = _Spot(name, index + 1)
    fields = _header_fields(lines[index], at)
    part = _choice(fields["part"], PART_IDS, "part", at)
    face = _choice(fields["face"], FACE_IDS, "face", at)
    model = _choice(fields["model"], MODELS, "model", at) if "model" in fields else None
    width, height = _size(fields, at)
    _check_size((part, face, model), (width, height), at)
    rows = tuple(row.rstrip() for row in lines[index + 1 : index + 1 + height])
    if len(rows) < height:
        raise at.error(f"block needs {height} rows, file ends after {len(rows)}")
    for offset, row in enumerate(rows, start=1):
        _check_row(row, width, at.below(offset))
    return GridBlock(part, face, model, rows, at.line)


def _blocks(text: str, name: str) -> Iterator[GridBlock]:
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        if not current:
            index += 1
            continue
        if not current.startswith(HEADER_PREFIX):
            raise _Spot(name, index + 1).error(f"expected a block header, got {current!r}")
        block = _read_block(lines, index, name)
        yield block
        index += 1 + len(block.rows)


def _collect(blocks: Iterator[GridBlock], name: str) -> dict[BlockKey, GridBlock]:
    collected: dict[BlockKey, GridBlock] = {}
    seen: dict[tuple[PartId, FaceId], set[Model | None]] = {}
    for block in blocks:
        part, face, model = block.key
        if block.key in collected:
            raise _Spot(name, block.line).error(f"duplicate block {part}.{face} model={model}")
        models = seen.setdefault((part, face), set())
        if models and (model is None or None in models):
            raise _Spot(name, block.line).error(f"{part}.{face} mixes shared and per-model blocks")
        models.add(model)
        collected[block.key] = block
    return collected


def _check_complete(template: GridTemplate) -> None:
    if not template.parts:
        raise _Spot(template.name, 1).error("template has no blocks")
    for part in sorted(template.parts):
        for face in FACE_IDS:
            for model in MODELS:
                try:
                    template.rows(part, face, model)
                except KeyError as exc:
                    raise _Spot(template.name, 1).error(f"missing block {exc.args[0]}") from exc


def parse_grid(text: str, name: str) -> GridTemplate:
    """Parse and fully validate one template."""
    template = GridTemplate(name, _collect(_blocks(text, name), name))
    _check_complete(template)
    return template


def load_grid(path: Path) -> GridTemplate:
    """Read and validate a `.grid` file; the template is named after the file stem."""
    return parse_grid(path.read_text(encoding="utf-8"), path.stem)


def load_template_dir(directory: Path) -> Mapping[str, GridTemplate]:
    """Every `.grid` file of a directory, validated, by template name."""
    paths = sorted(directory.glob(f"*{GRID_SUFFIX}"))
    return MappingProxyType({path.stem: load_grid(path) for path in paths})
