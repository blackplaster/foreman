from __future__ import annotations

from foreman.config import FactoryConfig
from foreman.models import (
    FactoryAssessment,
    Intervention,
    InterventionType,
    WorkerRecord,
    WorkerType,
)
from foreman.policy import FactoryPolicy


def with_scores(assessment: FactoryAssessment, **scores: float) -> FactoryAssessment:
    return assessment.model_copy(update=scores)


def active(state) -> None:
    state.workers.append(
        WorkerRecord(worker_id="worker-1", worker_type=WorkerType.CODING, mission="work")
    )
    state.active_workers.append("worker-1")
    state.iteration = 1


def test_continue(state, assessment) -> None:
    active(state)
    result = FactoryPolicy(FactoryConfig()).decide(state, assessment)
    assert result.action is InterventionType.CONTINUE


def test_start_worker(state, assessment) -> None:
    state.iteration = 1
    result = FactoryPolicy(FactoryConfig()).decide(state, assessment)
    assert result.action is InterventionType.START_WORKER


def test_start_verifier(state, assessment) -> None:
    state.iteration = 1
    value = with_scores(assessment, implementation_complete=0.9, needs_verification=0.9)
    assert (
        FactoryPolicy(FactoryConfig()).decide(state, value).action
        is InterventionType.START_VERIFIER
    )


def test_stop_off_track_worker(state, assessment) -> None:
    active(state)
    value = with_scores(assessment, work_off_track=0.95)
    result = FactoryPolicy(FactoryConfig()).decide(state, value)
    assert result.action is InterventionType.STOP_WORKER
    assert result.worker_id == "worker-1"


def test_stop_stuck_then_retry(state, assessment) -> None:
    active(state)
    policy = FactoryPolicy(FactoryConfig())
    stopped = policy.decide(state, with_scores(assessment, worker_stuck=0.95))
    assert stopped.action is InterventionType.STOP_WORKER
    state.active_workers.clear()
    state.latest_intervention = stopped
    assert policy.decide(state, assessment).action is InterventionType.RETRY_WORKER


def test_finish(state, assessment) -> None:
    state.iteration = 1
    state.verification_completed = True
    ready = with_scores(
        assessment,
        ready_to_finish=0.95,
        requirements_satisfied=0.95,
        tests_sufficient=0.95,
    )
    assert FactoryPolicy(FactoryConfig()).decide(state, ready).action is InterventionType.FINISH


def test_escalate(state, assessment) -> None:
    state.iteration = 1
    result = FactoryPolicy(FactoryConfig()).decide(
        state, with_scores(assessment, needs_human=0.95)
    )
    assert result.action is InterventionType.ESCALATE


def test_maximum_retries(state, assessment) -> None:
    state.iteration = 1
    state.retry_count = 1
    state.latest_intervention = Intervention(
        action=InterventionType.STOP_WORKER,
        reason="stuck",
        assessment_iteration=1,
    )
    assert FactoryPolicy(FactoryConfig(max_retries=1)).decide(
        state, assessment
    ).action is InterventionType.ESCALATE


def test_maximum_workers(state, assessment) -> None:
    state.iteration = 1
    state.workers.append(WorkerRecord(worker_id="w", worker_type=WorkerType.CODING, mission="x"))
    assert FactoryPolicy(FactoryConfig(max_workers=1)).decide(
        state, assessment
    ).action is InterventionType.ESCALATE


def test_verification_already_performed_is_not_repeated(state, assessment) -> None:
    state.iteration = 1
    state.verification_started = True
    state.verification_completed = True
    state.workers.append(WorkerRecord(worker_id="v", worker_type=WorkerType.VERIFIER, mission="x"))
    value = with_scores(assessment, implementation_complete=0.95, needs_verification=0.95)
    result = FactoryPolicy(FactoryConfig(max_workers=3)).decide(state, value)
    assert result.action is InterventionType.START_WORKER
    assert result.action is not InterventionType.START_VERIFIER


def test_maximum_iterations(state, assessment) -> None:
    state.iteration = state.max_iterations
    assert FactoryPolicy(FactoryConfig()).decide(
        state, assessment
    ).action is InterventionType.ESCALATE
