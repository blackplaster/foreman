# Runtime and event flow

## Components

```text
CodexWorker ──events──► FactoryRuntime ──snapshot──► ObservationBuilder
     ▲                       │                              │
     │                       │                              ▼
     └── intervention ◄── FactoryPolicy ◄──scores── JevForemanModel
                             │
                             ▼
                         RunStore
                    state.json + events.jsonl
```

- `CodexWorker` owns one subprocess and streams both pipes.
- `FactoryRuntime` owns lifecycle state, the event queue, and active worker tasks.
- `ObservationBuilder` gathers bounded worker, event, and Git evidence concurrently.
- `JevForemanModel` is the only module that imports the TypeSafe SDK.
- `FactoryPolicy` is pure deterministic decision logic.
- `RunStore` atomically replaces state and appends immutable events.

Simulation classes implement the same model and worker protocols. They exist for the demo and
offline tests; real runs default to Jev and Codex.

## One assessment cycle

1. A worker event enters the `asyncio.Queue`.
2. The watcher drains adjacent events and applies the minimum assessment interval.
3. Completion, failure, and stop events force an immediate cycle.
4. Git status/diff and current state become one bounded `FactoryObservation`.
5. The model returns nine probabilities.
6. Pydantic validates and normalizes the assessment.
7. Policy returns one legal `Intervention`.
8. Runtime applies it, persists state, and continues watching.

Foreman-generated events do not feed back into the queue, preventing the observer from triggering
itself recursively.

## Shutdown

Worker timeout, overall timeout, escalation, and cancellation all request graceful termination
first. A real worker targets the subprocess process group so child tools are not knowingly left
behind. After the grace period it sends a hard kill. Final state and the terminal event are
persisted before the runtime closes the model client.

## Reading the code

Start with these modules:

1. `src/foreman/runtime.py` — concurrency and lifecycle.
2. `src/foreman/policy.py` — allowed decisions and ordering.
3. `src/foreman/observation.py` — evidence boundaries.
4. `src/foreman/foreman/jev.py` — SDK isolation.
5. `src/foreman/workers/codex.py` — subprocess integration.
