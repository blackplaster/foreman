from __future__ import annotations

from typing import Protocol

from foreman.models import FactoryAssessment
from foreman.observation import FactoryObservation


class ForemanModelError(RuntimeError):
    """The semantic supervisor could not produce a valid assessment."""


class ForemanModel(Protocol):
    async def assess(self, observation: FactoryObservation) -> FactoryAssessment: ...

    async def close(self) -> None: ...

