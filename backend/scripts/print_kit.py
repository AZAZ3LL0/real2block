"""Write the PDFs for the owner's print and assembly check (docs/print-check.md).

Usage: uv run python scripts/print_kit.py [out_dir]
The reference skin gives every face its own color and an orientation marker, so a
wrongly turned or mirrored face is visible on the assembled figure.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from real2block.domain.papercraft.document import PapercraftService, PrintOptions
from real2block.domain.papercraft.layout import Paper, layout_pages
from real2block.domain.papercraft.net import build_net_part
from real2block.domain.papercraft.pdf import PdfRenderer
from real2block.domain.skin.geometry import PART_IDS, Model
from real2block.domain.skin.io import load_print_skin

ROOT = Path(__file__).resolve().parents[2]
SKIN = ROOT / "backend" / "tests" / "fixtures" / "reference_skin.png"


@dataclass(frozen=True, slots=True)
class KitSheet:
    """One PDF of the kit."""

    paper: Paper
    model: Model
    pixel_mm: float

    @property
    def filename(self) -> str:
        """File name that states what to check."""
        return f"{self.paper.lower()}-{self.model}-{self.pixel_mm:g}mm.pdf"


# Default size on both papers for both models, plus the smallest cell where the
# slim arm is tightest.
SHEETS = (
    KitSheet("A4", "classic", 5.0),
    KitSheet("Letter", "classic", 5.0),
    KitSheet("A4", "slim", 5.0),
    KitSheet("Letter", "slim", 5.0),
    KitSheet("A4", "slim", 3.0),
)


def expected_sizes(skin_png: bytes, sheet: KitSheet) -> list[str]:
    """Net outline sizes per page, tabs included, to measure on the print."""
    skin = load_print_skin(skin_png)
    nets = [build_net_part(skin, part, sheet.model, sheet.pixel_mm) for part in PART_IDS]
    lines = []
    for number, page in enumerate(layout_pages(nets, sheet.paper), start=1):
        parts = ", ".join(f"{p.net.code} {p.net.width:g}x{p.net.height:g}" for p in page.placements)
        lines.append(f"    net page {number}: {parts}")
    return lines


def main() -> None:
    """Render every sheet into the output directory and list what to measure."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", nargs="?", type=Path, default=ROOT / "print-kit")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    skin_png = SKIN.read_bytes()
    service = PapercraftService(PdfRenderer())
    for sheet in SHEETS:
        options = PrintOptions(
            model=sheet.model,
            paper=sheet.paper,
            pixel_mm=sheet.pixel_mm,
            mode="color",
            flatten_overlay=True,
            grid_lines=True,
            lang="ru",
        )
        target = args.out_dir / sheet.filename
        target.write_bytes(service.build(skin_png, options).pdf)
        print(target.relative_to(ROOT) if target.is_relative_to(ROOT) else target)
        print("\n".join(expected_sizes(skin_png, sheet)))


if __name__ == "__main__":
    main()
