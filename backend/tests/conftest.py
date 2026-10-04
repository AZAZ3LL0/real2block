import numpy as np
import pytest
from PIL import Image

from blockfold.domain.skin.skin import Skin
from tests.helpers import FIXTURES


@pytest.fixture(scope="session")
def reference_skin() -> Skin:
    with Image.open(FIXTURES / "reference_skin.png") as img:
        return Skin(np.asarray(img.convert("RGBA"), dtype=np.uint8))


@pytest.fixture(scope="session")
def reference_png() -> bytes:
    return (FIXTURES / "reference_skin.png").read_bytes()
