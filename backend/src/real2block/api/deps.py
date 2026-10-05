"""Dependency container and providers for route handlers."""

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request
from starlette.concurrency import run_in_threadpool

from real2block.domain.errors import InternalError
from real2block.domain.papercraft.document import PapercraftService
from real2block.domain.stylize.base import Stylizer, StylizerId

HEAVY_TIMEOUT_S = 10.0


class ReadinessProbe(Protocol):
    """Something whose readiness `/healthz` reports."""

    def is_ready(self) -> bool:
        """True when the component can serve requests."""
        ...


class HeavyRunner:
    """Runs CPU-bound calls in the thread pool with a hard timeout."""

    def __init__(self, timeout_s: float = HEAVY_TIMEOUT_S) -> None:
        self._timeout_s = timeout_s

    async def run[**P, T](self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Await `fn` off the event loop; a timeout becomes INTERNAL."""
        try:
            return await asyncio.wait_for(
                run_in_threadpool(fn, *args, **kwargs), timeout=self._timeout_s
            )
        except TimeoutError as exc:
            raise InternalError(f"{getattr(fn, '__qualname__', fn)} timed out") from exc


@dataclass(frozen=True, slots=True)
class Container:
    """Application object graph built once in `app_factory`."""

    face_model: ReadinessProbe
    papercraft: PapercraftService
    heavy: HeavyRunner
    stylizers: Mapping[StylizerId, Stylizer]


def get_container(request: Request) -> Container:
    """Container stored on the app at startup."""
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
