from __future__ import annotations

import os
import threading
import queue
import subprocess
from typing import Optional, Sequence, Dict

# Optional POSIX PTY support
try:
    import pty  # type: ignore
    import fcntl  # type: ignore
except Exception:
    pty = None     # type: ignore
    fcntl = None   # type: ignore


class TerminalIO:
    """Minimal IO backend used by ConsoleWindow."""
    proc: Optional[subprocess.Popen[bytes]] = None

    def read_nowait(self) -> Optional[bytes]:
        raise NotImplementedError

    def write(self, data: bytes) -> int:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


# ------------------------ Pipe backend (portable) ------------------------

class PipeTerminal(TerminalIO):
    """Portable pipe-backed terminal (Windows/macOS/Linux)."""
    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        if proc.stdout is None or proc.stdin is None:
            raise ValueError("Process must be started with stdin=PIPE and stdout=PIPE")
        self.proc = proc
        self._q: "queue.Queue[bytes]" = queue.Queue()
        self._closed = False
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    @classmethod
    def spawn(
        cls,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        start_new_session: bool = True,
    ) -> "PipeTerminal":
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=start_new_session,
        )
        return cls(proc)

    @classmethod
    def wrap_existing(cls, proc: subprocess.Popen[bytes]) -> "PipeTerminal":
        return cls(proc)

    def _reader(self) -> None:
        assert self.proc is not None
        streams = [self.proc.stdout, self.proc.stderr]
        import time
        while True:
            if self.proc.poll() is not None:
                # drain remaining
                for s in streams:
                    try:
                        if s is None:
                            continue
                        rem = s.read()
                        if rem:
                            self._q.put(rem)
                    except Exception:
                        pass
                break
            for s in streams:
                try:
                    if s is None:
                        continue
                    chunk = s.read(4096)
                    if chunk:
                        self._q.put(chunk)
                except Exception:
                    pass
            time.sleep(0.02)

    def read_nowait(self) -> Optional[bytes]:
        if self._closed:
            return None
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def write(self, data: bytes) -> int:
        if self._closed or self.proc is None or self.proc.stdin is None:
            return 0
        try:
            n = self.proc.stdin.write(data)
            self.proc.stdin.flush()
            return n
        except Exception:
            return 0

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass


# ------------------------ PTY backend (POSIX) ------------------------

class PtyTerminal(TerminalIO):
    """PTY-backed terminal (Linux/macOS). Gives 'real terminal' behavior (readline, colors)."""
    def __init__(
        self,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        term: str = "xterm-256color",
        start_new_session: bool = True,
    ) -> None:
        if os.name != "posix" or pty is None or fcntl is None:
            raise RuntimeError("PTY not available on this platform")

        if env is None:
            env = dict(os.environ)
        env = dict(env)
        env.setdefault("TERM", term)

        master_fd, slave_fd = pty.openpty()

        # Non-blocking master
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Duplicate the slave for stdio
        slave_in = os.fdopen(os.dup(slave_fd), "rb", buffering=0, closefd=True)
        slave_out = os.fdopen(os.dup(slave_fd), "wb", buffering=0, closefd=True)
        slave_err = os.fdopen(os.dup(slave_fd), "wb", buffering=0, closefd=True)

        self._master_fd = master_fd
        self._closed = False

        self.proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=slave_in,
            stdout=slave_out,
            stderr=slave_err,
            start_new_session=start_new_session,
            close_fds=True,
        )

        try:
            os.close(slave_fd)
        except OSError:
            pass

    def read_nowait(self) -> Optional[bytes]:
        if self._closed:
            return None
        try:
            return os.read(self._master_fd, 4096)
        except BlockingIOError:
            return None
        except OSError:
            return None

    def write(self, data: bytes) -> int:
        if self._closed:
            return 0
        try:
            return os.write(self._master_fd, data)
        except OSError:
            return 0

    def close(self) -> None:
        if self._closed:
            return
        try:
            os.close(self._master_fd)
        except OSError:
            pass
        self._closed = True


# ------------------------ Factory (for your separate spawner) ------------------------

def create_terminal(
    argv: Sequence[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    prefer_tty: bool = True,
    start_new_session: bool = True,
) -> TerminalIO:
    """
    Spawn a child attached to a terminal-like IO.
    On POSIX with prefer_tty=True, returns PtyTerminal; otherwise PipeTerminal.
    """
    if prefer_tty and os.name == "posix" and pty is not None and fcntl is not None:
        return PtyTerminal(argv, cwd=cwd, env=env, start_new_session=start_new_session)
    return PipeTerminal.spawn(argv, cwd=cwd, env=env, start_new_session=start_new_session)
