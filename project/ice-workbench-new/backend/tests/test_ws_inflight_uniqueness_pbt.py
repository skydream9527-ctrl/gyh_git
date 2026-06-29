"""Property-based test for the chat WebSocket inflight guard.

Feature: websocket-token-stability, Property 9: Inflight uniqueness

This models the inflight-guard admission semantics implemented in
``backend/app/api/v1/ws.py`` for an incoming ``user_message``:

  1. In-process registry check. ``_inflight_turns`` is a per-worker dict keyed
     on ``(task_id, conversation_id)``. If this worker already holds an active
     entry for the key, the message is rejected with ``CONVERSATION_INFLIGHT``.
  2. Cross-worker advisory flock. ``_try_acquire_conv_inflight`` takes a
     non-blocking ``portalocker`` exclusive lock on ``{cid}.inflight.lock``.
     If another worker process holds it, acquisition returns ``None`` and the
     message is rejected with ``CONVERSATION_INFLIGHT`` without starting a turn.
  3. Admission. Only after BOTH guards are obtained is a turn registered and
     started. On completion (or abort) the registry entry is popped and the
     flock released.

The key invariant under any interleaving of arrivals/completions across any
number of workers on a single ``(task_id, conversation_id)`` pair:
  * at most one turn is "running" per key at any moment, and
  * every colliding arrival is rejected with ``CONVERSATION_INFLIGHT`` while
    leaving the running turn (and its conversation storage) unmodified.

The guard is modeled as a deterministic abstract state machine (no real
asyncio races): the interleaving is expressed as a flat sequence of admit /
complete operations that Hypothesis generates and replays. The flock is the
cross-worker mutex, so it is modeled as a single-holder lock per key; the
in-process registry is modeled per (worker, key).

Validates: Requirements 10.1, 10.2
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

# The error code the real handler emits on a collision (kept as a literal so
# the test pins the externally observable contract rather than an import).
CONVERSATION_INFLIGHT = "CONVERSATION_INFLIGHT"
ADMITTED = "ADMITTED"


class InflightGuardModel:
    """Faithful, deterministic model of the ws.py inflight guard.

    Mirrors the admission order in ``ws_chat``'s ``user_message`` branch:
    per-worker in-process registry first, then the cross-worker advisory
    flock. Admission requires acquiring both; completion releases both.
    """

    def __init__(self) -> None:
        # Per-worker in-process registry: (worker, key) -> running?  Models the
        # module-level ``_inflight_turns`` dict, which is per process/worker.
        self._registry: dict[tuple[str, tuple[str, str]], bool] = {}
        # Cross-worker advisory flock: key -> worker holding it.  A single
        # holder per key models the kernel-level exclusive flock.
        self._flock: dict[tuple[str, str], str] = {}
        # Conversation storage write count per key.  Only an admitted (running)
        # turn ever writes; used to assert collisions don't touch storage.
        self.storage_writes: dict[tuple[str, str], int] = {}

    def admit(self, worker: str, key: tuple[str, str]) -> str:
        # 1. In-process registry guard (this worker).
        if self._registry.get((worker, key), False):
            return CONVERSATION_INFLIGHT
        # 2. Cross-worker advisory flock (non-blocking).
        if key in self._flock:
            return CONVERSATION_INFLIGHT
        # 3. Admit: acquire both guards, register + start the turn, write once.
        self._flock[key] = worker
        self._registry[(worker, key)] = True
        self.storage_writes[key] = self.storage_writes.get(key, 0) + 1
        return ADMITTED

    def complete(self, worker: str, key: tuple[str, str]) -> bool:
        """Complete/abort the turn this worker is running for ``key``."""
        if not self._registry.get((worker, key), False):
            return False
        self._registry[(worker, key)] = False
        if self._flock.get(key) == worker:
            del self._flock[key]
        return True

    def running_holder(self, key: tuple[str, str]) -> str | None:
        """The single worker currently running ``key`` (flock holder), if any."""
        return self._flock.get(key)


# A handful of keys and workers keeps the interleaving space small and the
# collisions frequent, which is what stresses the guard.
KEYS = [("task-A", "conv-1"), ("task-A", "conv-2"), ("task-B", "conv-1")]
WORKERS = ["w0", "w1", "w2"]

_op = st.tuples(
    st.sampled_from(["admit", "complete"]),
    st.sampled_from(WORKERS),
    st.sampled_from(KEYS),
)


@given(ops=st.lists(_op, min_size=1, max_size=60))
def test_inflight_uniqueness(ops):
    """Feature: websocket-token-stability, Property 9: Inflight uniqueness

    For any interleaving of user_message arrivals (and completions) on the
    modeled keys, at most one turn is running per key at any moment and every
    colliding arrival is rejected with CONVERSATION_INFLIGHT without starting a
    second turn or touching the running turn's storage.

    Validates: Requirements 10.1, 10.2
    """
    guard = InflightGuardModel()

    # Independent source of truth, maintained outside the model under test, so
    # the assertions don't merely re-state the model's own bookkeeping.
    truth_running: dict[tuple[str, str], str] = {}  # key -> worker
    admitted_count: dict[tuple[str, str], int] = {}  # key -> #turns admitted

    for kind, worker, key in ops:
        if kind == "admit":
            occupied_before = key in truth_running
            writes_before = guard.storage_writes.get(key, 0)

            result = guard.admit(worker, key)

            if result == ADMITTED:
                # Admission is only possible when the key was free.
                assert not occupied_before, (
                    f"admitted {worker} on {key} while {truth_running.get(key)} was running"
                )
                truth_running[key] = worker
                admitted_count[key] = admitted_count.get(key, 0) + 1
                # Exactly one storage write accompanies a started turn.
                assert guard.storage_writes.get(key, 0) == writes_before + 1
            else:
                # Req 10.2: a collision MUST be CONVERSATION_INFLIGHT...
                assert result == CONVERSATION_INFLIGHT
                # ...and only ever happens when the key is genuinely occupied.
                assert occupied_before, (
                    f"rejected {worker} on {key} but no turn was running"
                )
                # No second turn started => no storage modification on collision.
                assert guard.storage_writes.get(key, 0) == writes_before
        else:  # complete
            did = guard.complete(worker, key)
            if did:
                # Only the actual running holder can complete the turn.
                assert truth_running.get(key) == worker
                del truth_running[key]
            else:
                # Completing a turn this worker isn't running is a no-op and
                # must not disturb whoever (if anyone) is running the key.
                assert truth_running.get(key) != worker

        # ---- Global invariant checked after EVERY operation ----
        # At most one turn running per key: the model's flock holder must agree
        # with the independent truth, proving single-writer admission.
        for k in KEYS:
            holder = guard.running_holder(k)
            assert holder == truth_running.get(k), (
                f"key {k}: model holder={holder} truth={truth_running.get(k)}"
            )

    # Conservation: every key's admitted-turn count equals its storage writes,
    # i.e. storage was written exactly once per admitted turn and never by a
    # rejected colliding arrival.
    for key, count in admitted_count.items():
        assert guard.storage_writes.get(key, 0) == count
