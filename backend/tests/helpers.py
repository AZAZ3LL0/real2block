import io
from pathlib import Path

import numpy as np
import numpy.typing as npt
from PIL import Image

FIXTURES = Path(__file__).parent / "fixtures"


def png_bytes(pixels: npt.NDArray[np.uint8]) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="PNG")
    return buf.getvalue()


def blank(width: int = 64, height: int = 64) -> npt.NDArray[np.uint8]:
    return np.zeros((height, width, 4), dtype=np.uint8)
