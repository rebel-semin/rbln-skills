"""Flush the RBLN profiler on demand from inside whichever process owns the runtimes.

RBLN_PROFILER=1 makes every runtime collect traces, but .pb files are written
only by rebel's profiler.done(); a vLLM server never calls it, and its worker
processes are torn down (mp executor, shutdown timeout=0) without atexit or a
worker.shutdown() call we can rely on. So: a daemon thread in every Python
process of the container polls for a trigger file. When /traces/FLUSH appears,
each process that has rebel loaded calls profiler.start(cwd) + profiler.done()
(the sequence the batch-1 probe used) and leaves /traces/FLUSH.<pid>.done.
"""
import os
import sys
import threading
import time

TRIGGER = os.environ.get("RBLN_PROFILER_TRIGGER", "/traces/FLUSH")


def _watch() -> None:
    while not os.path.exists(TRIGGER):
        time.sleep(0.5)
    pid = os.getpid()
    if "rebel" not in sys.modules:
        sys.stderr.write(f"[rbln-prof-hook] pid={pid} trigger seen, no rebel here; skipping\n")
        sys.stderr.flush()
        return
    try:
        from rebel._C import profiler  # type: ignore
        profiler.start(os.getcwd())
        profiler.done()
        msg = f"flushed cwd={os.getcwd()}"
    except Exception as exc:
        msg = f"flush failed: {exc!r}"
    sys.stderr.write(f"[rbln-prof-hook] pid={pid} {msg}\n")
    sys.stderr.flush()
    try:
        with open(f"{TRIGGER}.{pid}.done", "w") as fh:
            fh.write(msg + "\n")
    except Exception:
        pass


if os.environ.get("RBLN_PROFILER") == "1":
    threading.Thread(target=_watch, name="rbln-prof-hook", daemon=True).start()
