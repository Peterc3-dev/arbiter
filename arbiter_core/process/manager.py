"""
Arbiter OS — Process Manager

Tracks long-running agent tasks as processes with PIDs.
MVP: run and kill only. No queue/pause/resume (Boo2: add when needed 3 times).

Processes are async tasks dispatched to CIN nodes. Each gets a PID,
tracks status, elapsed time, and the node/model executing it.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Coroutine, Any


class ProcessStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class ArbiterProcess:
    """A tracked process in Arbiter OS."""
    pid: int
    task_type: str
    description: str
    node: str
    model: str = ""
    status: ProcessStatus = ProcessStatus.RUNNING
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    result: str | None = None
    error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def elapsed_seconds(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def elapsed_display(self) -> str:
        s = int(self.elapsed_seconds)
        if s < 60:
            return f"{s}s"
        m, s = divmod(s, 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"


class ProcessManager:
    """Manages Arbiter OS processes — run and kill."""

    def __init__(self):
        self._processes: dict[int, ArbiterProcess] = {}
        self._next_pid: int = 1

    @property
    def all(self) -> list[ArbiterProcess]:
        return list(self._processes.values())

    @property
    def running(self) -> list[ArbiterProcess]:
        return [p for p in self._processes.values()
                if p.status == ProcessStatus.RUNNING]

    def get(self, pid: int) -> ArbiterProcess | None:
        return self._processes.get(pid)

    def run(
        self,
        task_type: str,
        description: str,
        node: str,
        model: str,
        coro: Coroutine[Any, Any, str],
    ) -> ArbiterProcess:
        """Start a new process from an async coroutine.

        Args:
            task_type: The routing task type (e.g. "code_transform")
            description: Human-readable task description
            node: CIN node executing the task
            model: Model being used
            coro: The async coroutine to execute

        Returns:
            The created ArbiterProcess with its PID
        """
        pid = self._next_pid
        self._next_pid += 1

        proc = ArbiterProcess(
            pid=pid,
            task_type=task_type,
            description=description,
            node=node,
            model=model,
        )

        async def _wrapper():
            try:
                result = await coro
                proc.result = result
                proc.status = ProcessStatus.COMPLETED
            except asyncio.CancelledError:
                proc.status = ProcessStatus.KILLED
            except Exception as e:
                proc.error = str(e)
                proc.status = ProcessStatus.FAILED
            finally:
                proc.end_time = time.time()

        proc._task = asyncio.create_task(_wrapper())
        self._processes[pid] = proc
        return proc

    def kill(self, pid: int) -> bool:
        """Kill a running process.

        Returns True if process was found and killed, False otherwise.
        """
        proc = self._processes.get(pid)
        if proc is None:
            return False
        if proc.status != ProcessStatus.RUNNING:
            return False
        if proc._task and not proc._task.done():
            proc._task.cancel()
        proc.status = ProcessStatus.KILLED
        proc.end_time = time.time()
        return True

    def clear_completed(self) -> int:
        """Remove non-running processes from the list. Returns count removed."""
        to_remove = [
            pid for pid, p in self._processes.items()
            if p.status != ProcessStatus.RUNNING
        ]
        for pid in to_remove:
            del self._processes[pid]
        return len(to_remove)
