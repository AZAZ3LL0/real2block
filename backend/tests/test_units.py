"""Config validation, model integrity, rate limiter and heavy-call timeout."""

import asyncio
import shutil
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from real2block.api.deps import HeavyRunner
from real2block.api.middleware import TokenBucket
from real2block.config import Settings
from real2block.domain.errors import InternalError
from real2block.domain.vision.face import ModelIntegrityError, YuNetModel

MODEL = Path("models/face_detection_yunet_2023mar.onnx")


def test_prod_requires_long_salt() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="prod", ip_hash_salt="short")
    assert Settings(app_env="prod", ip_hash_salt="x" * 32).is_prod


def test_invalid_env_value_fails_fast() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"face_score_threshold": 1.5})


def test_model_loads_when_checksum_matches() -> None:
    assert YuNetModel(MODEL, 0.8).is_ready()


def test_tampered_model_is_rejected(tmp_path: Path) -> None:
    model = tmp_path / MODEL.name
    shutil.copy(MODEL.parent / "SHA256SUMS", tmp_path / "SHA256SUMS")
    model.write_bytes(MODEL.read_bytes() + b"\0")
    with pytest.raises(ModelIntegrityError):
        YuNetModel(model, 0.8)


def test_missing_model_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ModelIntegrityError):
        YuNetModel(tmp_path / MODEL.name, 0.8)


def test_token_bucket_refills_over_an_hour() -> None:
    now = [0.0]
    bucket = TokenBucket(2, clock=lambda: now[0])
    assert [bucket.allow("a"), bucket.allow("a"), bucket.allow("a")] == [True, True, False]
    assert bucket.allow("b")
    now[0] = 1800.0
    assert bucket.allow("a")
    assert not bucket.allow("a")


def test_heavy_runner_times_out() -> None:
    runner = HeavyRunner(timeout_s=0.05)
    with pytest.raises(InternalError):
        asyncio.run(runner.run(time.sleep, 0.5))


def test_heavy_runner_returns_result() -> None:
    assert asyncio.run(HeavyRunner().run(sum, [1, 2, 3])) == 6
