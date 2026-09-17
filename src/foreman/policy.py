from __future__ import annotations

from dataclasses import dataclass

from foreman.config import FactoryConfig
from foreman.models import (
    FactoryAssessment,
    FactoryState,
    Intervention,
    InterventionType,
)


@dataclass(slots=True)
class FactoryPolicy:
    """Deterministic safety and lifecycle rules applied after semantic assessment."""

    config: FactoryConfig

    def decide(self, state: FactoryState, assessment: FactoryAssessment) -> Intervention:
        iteration = max(1, state.iteration)

        def result(
            action: InterventionType, reason: str, worker_id: str | None = None
        ) -> Intervention:
            return Intervention(
                action=action,
                reason=reason,
                assessment_iteration=iteration,
                worker_id=worker_id,
            )

        active_id = state.active_workers[0] if state.active_workers else None

        # Order is intentional: safety and hard limits win before productivity decisions.
        if assessment.needs_human >= self.config.human_threshold:
            return result(InterventionType.ESCALATE, "semantic assessment requires human input")

        if state.iteration >= state.max_iterations:
            return result(InterventionType.ESCALATE, "maximum Foreman iterations reached")

        if active_id and assessment.work_off_track >= self.config.off_track_threshold:
            return result(
                InterventionType.STOP_WORKER,
                "active worker appears off track",
                active_id,
            )

        if active_id and assessment.worker_stuck >= self.config.stuck_threshold:
            return result(
                InterventionType.STOP_WORKER,
                "active worker appears stuck",
                active_id,
            )

        if (
            not active_id
            and state.latest_intervention is not None
            and state.latest_intervention.action is InterventionType.STOP_WORKER
        ):
            retry_allowed = state.retry_count < self.config.max_retries
            worker_allowed = len(state.workers) < self.config.max_workers
            if retry_allowed and worker_allowed:
                return result(
                    InterventionType.RETRY_WORKER,
                    "retrying stopped worker with a fresh agent",
                )
            return result(InterventionType.ESCALATE, "worker retry limit reached")

        finish_ready = (
            assessment.ready_to_finish >= self.config.finish_threshold
            and assessment.requirements_satisfied >= self.config.requirements_threshold
            and assessment.tests_sufficient >= self.config.tests_threshold
        )
        verification_resolved = (
            state.verification_completed
            or assessment.needs_verification < self.config.verification_threshold
        )
        if not active_id and finish_ready and verification_resolved:
            return result(InterventionType.FINISH, "completion thresholds satisfied")

        should_verify = (
            not active_id
            and assessment.needs_verification >= self.config.verification_threshold
            and assessment.implementation_complete
            >= self.config.implementation_for_verification_threshold
            and not state.verification_started
        )
        if should_verify:
            if len(state.workers) >= self.config.max_workers:
                return result(
                    InterventionType.ESCALATE,
                    "verification needed but worker limit reached",
                )
            return result(InterventionType.START_VERIFIER, "independent verification is warranted")

        if not active_id:
            if len(state.workers) >= self.config.max_workers:
                return result(InterventionType.ESCALATE, "worker limit reached before completion")
            return result(InterventionType.START_WORKER, "meaningful implementation work remains")

        return result(InterventionType.CONTINUE, "active worker may continue")
