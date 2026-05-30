"""Pure-logic unit tests for the Process Manager.

Only imports ``arbiter_core.process.manager`` (standard library / asyncio).
No TUI or pyyaml dependency, so these run under a minimal environment.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from arbiter_core.process.manager import (
    ArbiterProcess,
    ProcessManager,
    ProcessStatus,
)


def test_elapsed_display_formats_seconds():
    p = ArbiterProcess(pid=1, task_type="t", description="d", node="n")
    p.start_time = 1000.0
    p.end_time = 1000.0 + 42
    assert p.elapsed_display == "42s"


def test_elapsed_display_formats_minutes():
    p = ArbiterProcess(pid=1, task_type="t", description="d", node="n")
    p.start_time = 0.0
    p.end_time = 125.0  # 2m 5s
    assert p.elapsed_display == "2m 5s"


def test_elapsed_display_formats_hours():
    p = ArbiterProcess(pid=1, task_type="t", description="d", node="n")
    p.start_time = 0.0
    p.end_time = 3661.0  # 1h 1m 1s
    assert p.elapsed_display == "1h 1m 1s"


def test_pids_increment_and_indices_track():
    async def scenario():
        pm = ProcessManager()
        assert pm.all == []
        assert pm.running == []

        async def sleeper():
            await asyncio.sleep(100)
            return "done"

        p1 = pm.run("a", "first", "node1", "model1", sleeper())
        p2 = pm.run("b", "second", "node2", "model2", sleeper())
        await asyncio.sleep(0)  # let wrapper tasks start awaiting their coroutines

        assert (p1.pid, p2.pid) == (1, 2)
        assert len(pm.all) == 2
        assert len(pm.running) == 2
        assert pm.get(1) is p1
        assert pm.get(999) is None

        # clean up tasks so the loop can close
        pm.kill(1)
        pm.kill(2)
        await asyncio.sleep(0)

    asyncio.run(scenario())


def test_kill_transitions_status_and_rejects_unknown():
    async def scenario():
        pm = ProcessManager()

        async def sleeper():
            await asyncio.sleep(100)
            return "done"

        proc = pm.run("t", "task", "node", "model", sleeper())
        await asyncio.sleep(0)  # let the wrapper task start awaiting the coroutine
        assert proc.status == ProcessStatus.RUNNING

        assert pm.kill(proc.pid) is True
        await asyncio.sleep(0.05)  # let cancellation propagate
        assert proc.status == ProcessStatus.KILLED
        assert proc.end_time is not None

        # killing again (already not running) returns False
        assert pm.kill(proc.pid) is False
        # killing an unknown pid returns False
        assert pm.kill(12345) is False

    asyncio.run(scenario())


def test_clear_completed_removes_only_finished():
    async def scenario():
        pm = ProcessManager()

        async def sleeper():
            await asyncio.sleep(100)
            return "done"

        keep = pm.run("t", "running", "node", "model", sleeper())
        gone = pm.run("t", "to-kill", "node", "model", sleeper())
        await asyncio.sleep(0)  # let wrapper tasks start awaiting their coroutines

        pm.kill(gone.pid)
        await asyncio.sleep(0.05)

        removed = pm.clear_completed()
        assert removed == 1
        assert [p.pid for p in pm.all] == [keep.pid]

        pm.kill(keep.pid)
        await asyncio.sleep(0)

    asyncio.run(scenario())
