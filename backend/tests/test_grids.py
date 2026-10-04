"""`.grid` format rules from tech.md §4.4 (v2 adds the optional model key)."""

import re
from pathlib import Path

import pytest

from real2block.domain.skin.geometry import FACE_IDS, FaceId, Model, PartId, face_rect
from real2block.domain.stylize.grids import (
    GridTemplate,
    TemplateError,
    load_template_dir,
    parse_grid,
)
from real2block.main import app_factory

MODELS: tuple[Model, ...] = ("classic", "slim")


def block(part: PartId, face: FaceId, symbol: str = "S", model: Model | None = None) -> str:
    rect = face_rect(part, face, model=model or "classic")
    header = f"# part={part} face={face} w={rect.w} h={rect.h}"
    if model:
        header += f" model={model}"
    return "\n".join([header, *([symbol * rect.w] * rect.h)])


def head(symbol: str = "S") -> str:
    return "\n\n".join(block("head", face, symbol) for face in FACE_IDS)


def arm(part: PartId = "right_arm") -> str:
    blocks = []
    for face in FACE_IDS:
        if face in ("right", "left"):
            blocks.append(block(part, face))
        else:
            blocks.extend(block(part, face, "T", model) for model in MODELS)
    return "\n\n".join(blocks)


def test_example_from_spec_parses() -> None:
    front = (
        "# part=head face=front w=8 h=8\n"
        "HHHHHHHH\nHHHHHHHH\nHSSSSSSH\nSSSSSSSS\n"
        "SWIsSIWS\nSSSsSSSS\nSSmMMmSS\nSSSSSSSS\n"
    )
    others = "\n".join(block("head", f) for f in FACE_IDS if f != "front")
    template = parse_grid(front + "\n" + others, "hair_test")
    assert template.parts == frozenset({"head"})
    assert template.rows("head", "front", "classic")[4] == "SWIsSIWS"
    assert template.rows("head", "front", "slim") == template.rows("head", "front", "classic")


def test_shared_block_serves_both_models() -> None:
    template = parse_grid(head("H"), "hair")
    for model in MODELS:
        assert template.rows("head", "top", model) == ("HHHHHHHH",) * 8


def test_model_blocks_follow_slim_geometry() -> None:
    template = parse_grid(arm(), "outfit")
    for model in MODELS:
        rect = face_rect("right_arm", "front", model=model)
        rows = template.rows("right_arm", "front", model)
        assert (len(rows[0]), len(rows)) == (rect.w, rect.h)


def test_blank_lines_and_trailing_spaces_are_ignored() -> None:
    text = "\n\n" + head().replace("SSSSSSSS\n", "SSSSSSSS   \n", 1) + "\n\n\n"
    assert isinstance(parse_grid(text, "hair"), GridTemplate)


def _replace_first(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new, 1)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (_replace_first(head(), "SSSSSSSS", "SSSSSSSX"), "unknown symbol 'X'"),
        (_replace_first(head(), "SSSSSSSS", "SSSSSSS."), "overlay-only"),
        (_replace_first(head(), "SSSSSSSS", "SSSSSSS"), "8 symbols wide"),
        (_replace_first(head(), "w=8 h=8", "w=8 h=7"), "header says (8, 7)"),
        (_replace_first(head(), "part=head", "part=tail"), "unknown part 'tail'"),
        (_replace_first(head(), "face=top", "face=side"), "unknown face 'side'"),
        (_replace_first(head(), " w=8", ""), "header keys"),
        (_replace_first(head(), "h=8", "h=8 layer=base"), "header keys"),
        (_replace_first(head(), "h=8", "h=8 h=8"), "repeated key"),
        (_replace_first(head(), "w=8", "w=eight"), "must be integers"),
        (_replace_first(head(), "h=8", "h=8 model=wide"), "unknown model"),
        (_replace_first(head(), "# part", "part"), "expected a block header"),
        (_replace_first(head(), "face=top", "face=front"), "duplicate block"),
        (head().rsplit("\n", 1)[0], "file ends after 7"),
        ("", "no blocks"),
    ],
)
def test_malformed_grid_is_rejected(text: str, message: str) -> None:
    with pytest.raises(TemplateError, match=re.escape(message)):
        parse_grid(text, "broken")


def test_error_names_file_and_line() -> None:
    text = _replace_first(head(), "SSSSSSSS", "SSSSSSSX")
    with pytest.raises(TemplateError, match=r"^broken\.grid:2: "):
        parse_grid(text, "broken")


def test_missing_face_is_rejected() -> None:
    text = "\n\n".join(block("head", face) for face in FACE_IDS if face != "back")
    with pytest.raises(TemplateError, match=r"missing block .*head\.back"):
        parse_grid(text, "hair")


def test_missing_slim_variant_is_rejected() -> None:
    text = arm().replace(block("right_arm", "back", "T", "slim"), "")
    with pytest.raises(TemplateError, match=r"right_arm\.back for slim"):
        parse_grid(text, "outfit")


def test_shared_block_must_fit_both_models() -> None:
    text = arm().replace(block("right_arm", "front", "T", "slim"), "")
    text = text.replace(" model=classic", "", 1)
    with pytest.raises(TemplateError, match="for slim, header says"):
        parse_grid(text, "outfit")


def test_shared_and_model_blocks_do_not_mix() -> None:
    text = head() + "\n\n" + block("head", "top", "H", "slim")
    with pytest.raises(TemplateError, match="mixes shared and per-model"):
        parse_grid(text, "hair")


def test_directory_loads_every_grid(tmp_path: Path) -> None:
    (tmp_path / "hair_a.grid").write_text(head(), encoding="utf-8")
    (tmp_path / "outfit_b.grid").write_text(arm(), encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    assert sorted(load_template_dir(tmp_path)) == ["hair_a", "outfit_b"]


def test_app_does_not_start_with_a_broken_template(tmp_path: Path) -> None:
    (tmp_path / "hair_bad.grid").write_text(head().replace("S", "?", 1), encoding="utf-8")
    with pytest.raises(TemplateError, match=r"hair_bad\.grid"):
        app_factory(templates_dir=tmp_path)
