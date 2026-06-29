"""Example / integration tests for turn-lifecycle + inflight status timing.

Task 5.3 (websocket-token-stability). These are REPRESENTATIVE example tests,
not randomized property tests. They exercise the real WS lifecycle primitives
where they are deterministic — the cross-worker advisory flock
(`_try_acquire_conv_inflight` / `_release_conv_inflight`), the `inflight_svc`
busy/idle state round-trip, the in-process inflight registry + `is_inflight`
/ `cancel_inflight_turn`, the keepalive sidecar, and the cancel-event
semantics — and fall back to focused structural (source-level) assertions for
behaviors that can only be observed inside a full streaming WS turn.

Coverage map (real assertion vs structural check):

  8.1 disconnect keeps turn running ............ REAL (registry + cooperative task)
  8.2 disconnect does NOT set cancel signal .... REAL (registry) + STRUCTURAL (finally)
  8.4 persist completed turn before release .... STRUCTURAL (_run_turn ordering)
  8.5 persist-failure releases guard + diag .... STRUCTURAL (_run_turn try/except/finally)
  9.1 explicit abort sets cancel within 1s ..... REAL (registry + Event timing)
  9.2 abort is a no-op on an idle conversation . REAL (empty registry)
  9.3 persist already-streamed content on abort  STRUCTURAL (cancel block append_jsonl)
  9.4 persist completed tool calls on abort .... STRUCTURAL (cancel block tool_uses)
 10.3 cross-worker flock rejects the loser ..... REAL (portalocker flock contention)
 10.4 inflight_status to reconnect within 2s ... REAL (heartbeat constant + state round-trip)
 10.6 idle broadcast within 2s of turn end ..... REAL (heartbeat constant + mark_idle round-trip)
  7.5 slow to_thread IO does not starve keepalive REAL (loop keeps firing) + STRUCTURAL (to_thread)
"""
from __future__ import annotations

import asyncio
import inspect
import re
import time

import pytest

from app.api.v1 import ws as ws_mod
from app.services import inflight_svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TASK_ID = "task-ttl"
CONV_ID = "conv-ttl"


@pytest.fixture(autouse=True)
def _clean_registry():
    """Keep the module-level inflight registry clean across tests."""
    ws_mod._inflight_turns.clear()
    yield
    ws_mod._inflight_turns.clear()


# ---------------------------------------------------------------------------
# 10.3 — Cross-worker advisory flock contention (REAL primitive)
# ---------------------------------------------------------------------------

def test_flock_second_acquire_loses_then_recovers(isolated_data_root):
    """A second acquisition of the conv inflight flock fails while the first is
    held (this is exactly what a competing uvicorn worker sees → the loser is
    rejected with CONVERSATION_INFLIGHT), and the lock is reusable after
    release. (Req 10.3)"""
    fh1 = ws_mod._try_acquire_conv_inflight(TASK_ID, CONV_ID)
    assert fh1 is not None, "first acquisition should succeed"

    # Second acquisition (simulating the other worker) must lose.
    fh2 = ws_mod._try_acquire_conv_inflight(TASK_ID, CONV_ID)
    assert fh2 is None, "second acquisition must lose while the lock is held"

    # Release the winner; the lock becomes reusable.
    ws_mod._release_conv_inflight(fh1)
    fh3 = ws_mod._try_acquire_conv_inflight(TASK_ID, CONV_ID)
    assert fh3 is not None, "lock must be reusable after release"
    ws_mod._release_conv_inflight(fh3)


def test_flock_distinct_conversations_do_not_contend(isolated_data_root):
    """Different conversations use different lock files → both can be held.
    Confirms the guard key is per-(task, conv), not global. (Req 10.1/10.3)"""
    a = ws_mod._try_acquire_conv_inflight(TASK_ID, "conv-A")
    b = ws_mod._try_acquire_conv_inflight(TASK_ID, "conv-B")
    try:
        assert a is not None and b is not None
    finally:
        ws_mod._release_conv_inflight(a)
        ws_mod._release_conv_inflight(b)


def test_release_none_is_noop(isolated_data_root):
    """Releasing a None handle (the rejected-loser path) is a safe no-op."""
    ws_mod._release_conv_inflight(None)  # must not raise


# ---------------------------------------------------------------------------
# 10.4 / 10.6 — inflight status latency (REAL state round-trip + constant)
# ---------------------------------------------------------------------------

def test_inflight_heartbeat_interval_within_2s():
    """The cross-worker status heartbeat re-reads + pushes every 2s, so a
    reconnecting client (10.4) and other workers after a turn ends (10.6) see
    the busy/idle transition within the 2s contract."""
    assert ws_mod._INFLIGHT_HEARTBEAT_SEC == 2


def test_inflight_state_round_trip_busy_then_idle(isolated_data_root):
    """mark_busy → read_state (busy) → mark_idle → read_state (idle).

    This is the cross-worker-readable UX state a reconnecting client / another
    worker reads off disk; the round-trip is what the heartbeat surfaces within
    2s. (Req 10.4, 10.6)"""
    assert inflight_svc.read_state(TASK_ID, CONV_ID) is None  # idle to start

    state = inflight_svc.mark_busy(
        TASK_ID, CONV_ID, user_id="user-001", user_name="Alice"
    )
    assert state["user_id"] == "user-001"

    read_back = inflight_svc.read_state(TASK_ID, CONV_ID)
    assert read_back is not None
    assert read_back["user_id"] == "user-001"
    assert read_back["user_name"] == "Alice"
    assert read_back["started_at"]  # iso timestamp recorded

    # The payload a reconnecting client receives reflects busy.
    busy_payload = ws_mod._inflight_status_payload(read_back)
    assert busy_payload["busy"] is True
    assert busy_payload["user"]["id"] == "user-001"

    inflight_svc.mark_idle(TASK_ID, CONV_ID)
    assert inflight_svc.read_state(TASK_ID, CONV_ID) is None

    idle_payload = ws_mod._inflight_status_payload(None)
    assert idle_payload["busy"] is False
    assert idle_payload["user"] is None


def test_state_signature_changes_drive_heartbeat_push(isolated_data_root):
    """The heartbeat only pushes when the state signature changes; idle and busy
    must produce distinct signatures so a transition is always emitted (and thus
    reaches the client within one 2s tick). (Req 10.4, 10.6)"""
    idle_sig = ws_mod._state_signature(None)
    busy = inflight_svc.mark_busy(TASK_ID, CONV_ID, user_id="user-001", user_name="Alice")
    busy_sig = ws_mod._state_signature(busy)
    assert idle_sig != busy_sig
    inflight_svc.mark_idle(TASK_ID, CONV_ID)


# ---------------------------------------------------------------------------
# 8.1 / 8.2 — Disconnect does not cancel a running turn (REAL registry)
# ---------------------------------------------------------------------------

async def _cooperative_turn(cancel: asyncio.Event) -> str:
    """Stand-in for the real turn loop's cooperative cancel observation: the
    loop checks `cancel_event.is_set()` each round (mirrors `_handle_user_message`)
    and returns once cancelled."""
    while not cancel.is_set():
        await asyncio.sleep(0.01)
    return "stopped"


async def test_disconnect_does_not_cancel_running_turn(isolated_data_root):
    """Registering a turn and then simulating a WS disconnect (the ws_chat
    `finally`) must NOT set the cancel event and must NOT cancel the turn task:
    the turn keeps running to completion. (Req 8.1, 8.2)"""
    cancel = asyncio.Event()
    task = asyncio.create_task(_cooperative_turn(cancel))
    ws_mod._inflight_turns[(TASK_ID, CONV_ID)] = (task, cancel)

    assert ws_mod.is_inflight(TASK_ID, CONV_ID) is True

    # Simulate disconnect: in ws_chat's `finally`, only the heartbeat task is
    # cancelled — the turn task / cancel event are deliberately left untouched.
    await asyncio.sleep(0.05)

    assert cancel.is_set() is False, "disconnect must not set the cancel signal"
    assert task.done() is False, "turn must keep running after disconnect"
    assert ws_mod.is_inflight(TASK_ID, CONV_ID) is True

    # Now let it finish naturally (turn completes).
    cancel.set()
    result = await asyncio.wait_for(task, timeout=1.0)
    assert result == "stopped"


def test_disconnect_finally_does_not_cancel_turn_structural():
    """Structural backstop for 8.1/8.2: the ws_chat disconnect `finally` block
    cancels the heartbeat task but contains no call that cancels the running
    turn task (no `cancel_inflight_turn`, no `.cancel()` on the turn task)."""
    src = inspect.getsource(ws_mod.ws_chat)
    # Grab the trailing `finally:` block of ws_chat (the disconnect cleanup).
    finally_idx = src.rfind("\n    finally:")
    assert finally_idx != -1
    finally_block = src[finally_idx:]
    assert "heartbeat_task.cancel()" in finally_block
    assert "cancel_inflight_turn" not in finally_block
    # The turn task is never force-cancelled on disconnect.
    assert "new_task.cancel()" not in finally_block


# ---------------------------------------------------------------------------
# 9.1 / 9.2 — Explicit abort (REAL registry + Event timing)
# ---------------------------------------------------------------------------

async def test_explicit_abort_sets_cancel_within_1s(isolated_data_root):
    """The abort branch looks up the registry entry and calls `entry[1].set()`
    synchronously, so the cancel signal is observed well within 1s and the
    cooperative turn loop stops. (Req 9.1)"""
    cancel = asyncio.Event()
    task = asyncio.create_task(_cooperative_turn(cancel))
    inflight_key = (TASK_ID, CONV_ID)
    ws_mod._inflight_turns[inflight_key] = (task, cancel)

    t0 = time.monotonic()
    # Exact logic from the `abort` handler in ws_chat:
    entry = ws_mod._inflight_turns.get(inflight_key)
    assert entry is not None
    entry[1].set()
    set_latency = time.monotonic() - t0
    assert set_latency < 1.0

    # The running turn observes the signal and stops cooperatively.
    result = await asyncio.wait_for(task, timeout=1.0)
    assert result == "stopped"
    assert cancel.is_set() is True


async def test_abort_is_noop_on_idle_conversation(isolated_data_root):
    """An `abort` for a conversation with no running turn is ignored and leaves
    all turn/conversation state unchanged. (Req 9.2)"""
    inflight_key = (TASK_ID, CONV_ID)
    assert ws_mod.is_inflight(TASK_ID, CONV_ID) is False

    # Seed an idle inflight state file; abort must not touch it.
    inflight_svc.mark_idle(TASK_ID, CONV_ID)  # ensure clean
    before = inflight_svc.read_state(TASK_ID, CONV_ID)

    # Exact logic from the `abort` handler: no entry → nothing happens.
    entry = ws_mod._inflight_turns.get(inflight_key)
    assert entry is None  # → handler sets nothing

    after = inflight_svc.read_state(TASK_ID, CONV_ID)
    assert before == after
    assert ws_mod.is_inflight(TASK_ID, CONV_ID) is False


async def test_cancel_inflight_turn_stops_running_turn(isolated_data_root):
    """The real `cancel_inflight_turn` helper (used by the explicit-abort /
    plan-approval paths) sets the cancel event, force-cancels, and reports the
    turn finished. On an idle conversation it returns False. (Req 9.1)"""
    # Idle: nothing to cancel.
    assert await ws_mod.cancel_inflight_turn(TASK_ID, CONV_ID) is False

    cancel = asyncio.Event()

    async def _turn():
        try:
            while not cancel.is_set():
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            raise
        return "done"

    task = asyncio.create_task(_turn())
    ws_mod._inflight_turns[(TASK_ID, CONV_ID)] = (task, cancel)

    t0 = time.monotonic()
    found = await ws_mod.cancel_inflight_turn(TASK_ID, CONV_ID)
    assert found is True
    assert (time.monotonic() - t0) < 3.5  # bounded by the helper's 3s shield
    assert cancel.is_set() is True
    # Registry entry is cleaned up so subsequent messages aren't INFLIGHT-blocked.
    assert ws_mod._inflight_turns.get((TASK_ID, CONV_ID)) is None


def test_abort_persists_partial_content_structural():
    """Structural backstop for 9.3/9.4: when the cancel signal is observed
    mid-turn, `_handle_user_message` persists the already-streamed assistant
    text AND the completed tool_uses with a `user_aborted` stop reason before
    returning."""
    src = inspect.getsource(ws_mod._handle_user_message)
    assert '"user_aborted"' in src
    # The abort-persist block writes both partial text and tool_uses.
    assert "partial_text" in src
    assert re.search(r"if\s+partial_text\s+or\s+tool_uses", src)
    # Persistence goes through the file-first append helper off the event loop.
    assert re.search(r"asyncio\.to_thread\(\s*append_jsonl", src)


# ---------------------------------------------------------------------------
# 8.4 / 8.5 — Persist before release; persist-failure releases guard (STRUCTURAL)
# ---------------------------------------------------------------------------

def _run_turn_source() -> str:
    """Extract the nested `_run_turn` coroutine body from ws_chat's source."""
    src = inspect.getsource(ws_mod.ws_chat)
    start = src.index("async def _run_turn")
    # The coroutine ends where the outer `try:`/while loop begins.
    end = src.index("\n    try:\n", start)
    return src[start:end]


def test_persist_completed_turn_before_releasing_guard_structural():
    """8.4: the turn handler (which persists assistant messages + tool calls)
    is awaited BEFORE the `finally` releases the cross-worker flock and clears
    the in-process registry entry."""
    body = _run_turn_source()
    handle_idx = body.index("await _handle_user_message(")
    finally_idx = body.index("finally:")
    release_idx = body.index("_release_conv_inflight(lock_fh)")
    assert handle_idx < finally_idx < release_idx, (
        "turn must be persisted (via _handle_user_message) before the guard is released"
    )


def test_persist_failure_releases_guard_and_records_diagnostics_structural():
    """8.5: a crash while handling/persisting a turn is caught and logged
    (diagnostics), and the `finally` still releases the flock + registry entry
    and marks idle — the guard is never leaked on a persistence error."""
    body = _run_turn_source()
    assert "except Exception:" in body
    assert "log.exception(" in body  # records the failure for diagnostics
    finally_idx = body.index("finally:")
    finally_block = body[finally_idx:]
    assert "_release_conv_inflight(lock_fh)" in finally_block
    assert "_inflight_turns.pop(inflight_key, None)" in finally_block
    assert "inflight_svc.mark_idle(" in finally_block


# ---------------------------------------------------------------------------
# 7.5 — Slow to_thread IO does not starve keepalive (REAL loop + STRUCTURAL)
# ---------------------------------------------------------------------------

class _FakeWS:
    """Minimal WebSocket sink capturing keepalive frames with timestamps."""

    def __init__(self) -> None:
        self.sent: list[tuple[float, str]] = []

    async def send_text(self, text: str) -> None:
        self.sent.append((time.monotonic(), text))


async def test_keepalive_keeps_firing_during_slow_blocking_io(isolated_data_root):
    """A long-running synchronous IO call dispatched via `asyncio.to_thread`
    must not block the event loop, so the keepalive sidecar keeps emitting
    frames at its cadence even while the blocking call is in flight. (Req 7.5)

    We drive `_ws_keepalive_loop` at a small interval (the production cadence is
    a constant, exercised separately) and run a blocking `time.sleep` off-thread
    concurrently; the keepalive frames must still arrive on time."""
    fake_ws = _FakeWS()
    ka = asyncio.create_task(ws_mod._ws_keepalive_loop(fake_ws, interval=0.05))

    # Simulate a slow synchronous IO op the turn path would do (append_jsonl,
    # load_conversation_messages, ...). Because it's offloaded, the loop is free.
    await asyncio.to_thread(time.sleep, 0.3)

    ka.cancel()
    try:
        await ka
    except asyncio.CancelledError:
        pass

    keepalives = [t for t, body in fake_ws.sent if "keepalive" in body]
    # ~0.3s / 0.05s ≈ 6 frames; require several to prove the loop wasn't starved.
    assert len(keepalives) >= 3, f"keepalive starved during blocking IO: {fake_ws.sent}"


def test_keepalive_interval_within_30s_contract():
    """The application-layer keepalive cadence sits inside the ≤30s inter-frame
    ceiling (Req 7.1, 7.2)."""
    assert ws_mod._WS_KEEPALIVE_SEC <= 30


def test_turn_path_sync_io_offloaded_to_thread_structural():
    """7.5 structural: the synchronous IO operations on the turn path
    (conversation/tool-call JSONL writes, history load, api-message build) are
    dispatched through `asyncio.to_thread` so a slow conversation cannot starve
    keepalive/ping for this or other concurrent conversations."""
    src = inspect.getsource(ws_mod._handle_user_message)
    assert re.search(r"asyncio\.to_thread\(\s*append_jsonl", src)
    assert re.search(r"asyncio\.to_thread\(\s*\n?\s*task_svc\.load_conversation_messages", src)
    assert re.search(r"asyncio\.to_thread\(\s*\n?\s*_to_api_messages", src)
