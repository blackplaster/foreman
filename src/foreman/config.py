from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class FactoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_min_interval_seconds: float = Field(default=5.0, ge=0.0)
    periodic_assessment_seconds: float = Field(default=30.0, gt=0.0)
    jev_timeout_seconds: float = Field(default=10.0, gt=0.0)
    worker_timeout_seconds: float = Field(default=3_600.0, gt=0.0)
    overall_timeout_seconds: float = Field(default=7_200.0, gt=0.0)
    graceful_termination_seconds: float = Field(default=5.0, ge=0.0)
    max_concurrent_workers: int = Field(default=1, ge=1)
    max_workers: int = Field(default=3, ge=1)
    max_retries: int = Field(default=1, ge=0)
    max_iterations: int = Field(default=20, ge=1)

    human_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    off_track_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    stuck_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    verification_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    finish_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    requirements_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    tests_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    implementation_for_verification_threshold: float = Field(default=0.75, ge=0.0, le=1.0)

    diff_limit: int = Field(default=20_000, ge=100)
    output_limit: int = Field(default=12_000, ge=100)
    field_limit: int = Field(default=50_000, ge=100)
    event_history_limit: int = Field(default=30, ge=1)
    worker_history_limit: int = Field(default=10, ge=1)

    @classmethod
    def from_environment(cls) -> FactoryConfig:
        mapping: dict[str, tuple[str, type]] = {
            "FOREMAN_ASSESSMENT_MIN_INTERVAL_SECONDS": (
                "assessment_min_interval_seconds",
                float,
            ),
            "FOREMAN_PERIODIC_ASSESSMENT_SECONDS": ("periodic_assessment_seconds", float),
            "FOREMAN_JEV_TIMEOUT_SECONDS": ("jev_timeout_seconds", float),
            "FOREMAN_WORKER_TIMEOUT_SECONDS": ("worker_timeout_seconds", float),
            "FOREMAN_OVERALL_TIMEOUT_SECONDS": ("overall_timeout_seconds", float),
            "FOREMAN_MAX_WORKERS": ("max_workers", int),
            "FOREMAN_MAX_RETRIES": ("max_retries", int),
            "FOREMAN_MAX_ITERATIONS": ("max_iterations", int),
        }
        values: dict[str, object] = {}
        for env_name, (field_name, converter) in mapping.items():
            value = os.getenv(env_name)
            if value is not None:
                values[field_name] = converter(value)
        return cls(**values)
