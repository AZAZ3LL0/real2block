# Print and assembly check

The owner prints and assembles the figure on A4 and on Letter before the release. Anything that does not fit is reported as a CONTRACT GAP; geometry, golden files and tests are not adjusted to match the paper.

## 1. Make the kit

```bash
cd backend
uv run python scripts/print_kit.py      # writes ../print-kit/*.pdf and lists the sizes to measure
```

| File | Why |
|---|---|
| `a4-classic-5mm.pdf` | default settings; must be exactly 2 net pages |
| `letter-classic-5mm.pdf` | Letter margins and page breaks |
| `a4-slim-5mm.pdf`, `letter-slim-5mm.pdf` | 3-pixel arms |
| `a4-slim-3mm.pdf` | smallest cell, tightest slim arm tabs |

All sheets use `tests/fixtures/reference_skin.png`: every face has its own color and a white (top-left) and black (top-right) marker pixel, so a turned or mirrored face is visible.

## 2. Print

- Printer dialog: scale 100% / "Actual size", no "Fit to page". The PDF asks for this by default; check it was not overridden.
- Plain 80 g/m² paper is enough for the check; 160–200 g/m² is what the figure is meant for.

## 3. Measure, before cutting

- The 50 mm ruler on every net page: 50 ± 0.5 mm.
- Net outlines (tabs included) against the sizes printed by `print_kit.py`, ± 1 mm. At 5 mm: head 166 × 132, body 126 × 112, classic limbs 86 × 112, slim arms 76 × 112.
- Nothing is clipped by the printer's unprintable margin.

## 4. Assemble and compare

Follow the instruction pages of the PDF. Then compare the figure with the 3D preview of the same skin (Upload → «Готовый скин» → `reference_skin.png`, rotate the model):

- every face has the color shown in the preview, at the same place;
- marker pixels sit in the same corners as in the preview, in particular on `top` and `bottom` (tech.md §4.2);
- each tab label `X-n` meets the edge with the same label;
- assembled height at 5 mm is 160 mm; head 40 × 40 × 40 mm;
- limbs attach where step 6 of the instruction says.

## 5. Record

| Sheet | Ruler | Outlines | Faces and markers | Tabs | Height | Notes |
|---|---|---|---|---|---|---|
| A4 classic 5 mm | | | | | | |
| Letter classic 5 mm | | | | | | |
| A4 slim 5 mm | | | | | | |
| Letter slim 5 mm | | | | | | |
| A4 slim 3 mm | | | | | | |

For every mismatch write a CONTRACT GAP (what is wrong, which sheet, the measured value, the proposed rule) and attach a photo of the part.

## Known gap

At `pixel_mm < 4` the top and bottom edges of a slim arm (3 cells) are shorter than the two 45° slopes of a 6 mm tab, so tabs `RA-C`, `RA-F`, `LA-C`, `LA-F` come out as a crossed shape. `test_tab_sides_do_not_cross` marks this as `xfail` until §4.2 defines the short-edge tab.
