"""Run ``run_hook`` in a child process and SIGKILL it mid-hook, as an OOM kill would.

The hook's ``finally`` copy-back never runs; only what was mirrored while the hook
ran reaches the installer's state directory.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

_CHILD = r'''
import json, os, subprocess, sys, time
from pathlib import Path
from installer.hook_process import run_hook

state_receipt, output, ready, steps = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
sample = Path(sys.argv[5]); sample.mkdir(exist_ok=True)
script = sample / "hook.sh"; script.write_text("")

def hook(argv, env):
    receipt = Path(env["BKN_SAMPLE_RECEIPT"])
    for raw in steps:
        if raw is None:
            continue
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(raw)
        temporary.replace(receipt)
        time.sleep(0.05)
    Path(env["BKN_SAMPLE_OUTPUT"]).write_text('{"ok": true}')
    Path(ready).write_text("hook is creating resources")
    time.sleep(600)
    return subprocess.CompletedProcess(argv, 0)

run_hook(sample, script, hook, {"BKN_SAMPLE_RECEIPT": state_receipt, "BKN_SAMPLE_OUTPUT": output})
'''


def kill_during_hook(state_receipt, scratch, receipt_steps, *, settle=1.0):
    """Write each receipt snapshot from the hook, then SIGKILL the service process."""
    scratch = Path(scratch)
    output, ready = scratch / "output.json", scratch / "ready"
    Path(state_receipt).parent.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parents[2]
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD, str(state_receipt), str(output), str(ready), json.dumps(receipt_steps),
         str(scratch / "sample")],
        cwd=repository, env={**os.environ, "PYTHONPATH": str(repository)})
    try:
        deadline = time.monotonic() + 30
        while not ready.exists():
            if child.poll() is not None or time.monotonic() > deadline:
                raise AssertionError("hook child did not reach the kill point")
            time.sleep(0.05)
        time.sleep(settle)  # Several mirror intervals.
    finally:
        child.send_signal(signal.SIGKILL)
        child.wait()
    return output
