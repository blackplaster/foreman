from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from foreman.models import EventType, WorkerRecord, WorkerStatus, WorkerType
from foreman.workers import CodexWorker, FakeWorker


def record() -> WorkerRecord:
    return WorkerRecord(worker_id="worker-1", worker_type=WorkerType.CODING, mission="do work")


def test_subprocess_command_construction(tmp_path) -> None:
    command = CodexWorker(executable="codex").command(tmp_path, "do work")
    assert command == [
        "codex",
        "exec",
        "--cd",
        str(tmp_path.resolve()),
        "--sandbox",
        "workspace-write",
        "--color",
        "never",
        "--json",
        "do work",
    ]


@pytest.mark.asyncio
async def test_fake_worker_streaming_and_success(tmp_path) -> None:
    events = []

    async def emit(event_type, payload) -> None:
        events.append((event_type, payload))

    result = await FakeWorker(output_lines=["a", "b"], delay_seconds=0).run(
        record(), tmp_path, emit, 1
    )
    assert result.status is WorkerStatus.COMPLETED
    assert result.stdout == "a\nb\n"
    assert [event[0] for event in events] == [EventType.WORKER_OUTPUT] * 2


@pytest.mark.asyncio
async def test_fake_worker_failed_exit(tmp_path) -> None:
    async def emit(*args) -> None:
        return None

    result = await FakeWorker(exit_code=2, delay_seconds=0).run(record(), tmp_path, emit, 1)
    assert result.status is WorkerStatus.FAILED
    assert result.exit_code == 2


@pytest.mark.asyncio
async def test_fake_worker_timeout(tmp_path) -> None:
    async def emit(*args) -> None:
        return None

    result = await FakeWorker(wait_forever=True, output_lines=[], delay_seconds=0).run(
        record(), tmp_path, emit, 0.01
    )
    assert result.status is WorkerStatus.TIMED_OUT


@pytest.mark.asyncio
async def test_fake_worker_graceful_termination(tmp_path) -> None:
    async def emit(*args) -> None:
        return None

    worker = FakeWorker(wait_forever=True, output_lines=[], delay_seconds=0)
    task = asyncio.create_task(worker.run(record(), tmp_path, emit, 1))
    await asyncio.sleep(0)
    await worker.terminate("off track")
    result = await task
    assert result.status is WorkerStatus.STOPPED
    assert result.termination_reason == "off track"


@pytest.mark.asyncio
async def test_fake_worker_cancellation(tmp_path) -> None:
    async def emit(*args) -> None:
        return None

    worker_record = record()
    worker = FakeWorker(wait_forever=True, output_lines=[], delay_seconds=0)
    task = asyncio.create_task(worker.run(worker_record, tmp_path, emit, 10))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert worker_record.status is WorkerStatus.CANCELLED


class Process:
    def __init__(self, stdout: bytes, stderr: bytes, returncode: int = 0) -> None:
        self.stdout = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stdout.feed_eof()
        self.stderr = asyncio.StreamReader()
        self.stderr.feed_data(stderr)
        self.stderr.feed_eof()
        self.returncode = None
        self._final = returncode
        self.pid = 12345

    async def wait(self) -> int:
        self.returncode = self._final
        return self._final

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


@pytest.mark.asyncio
async def test_codex_worker_streams_both_pipes(monkeypatch, tmp_path) -> None:
    process = Process(b'{"type":"item"}\n', b"warning\n")

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    events = []

    async def emit(event_type, payload) -> None:
        events.append(payload)

    result = await CodexWorker().run(record(), Path(tmp_path), emit, 1)
    assert result.status is WorkerStatus.COMPLETED
    assert '"type"' in result.stdout
    assert "warning" in result.stderr
    assert {event["stream"] for event in events} == {"stdout", "stderr"}

