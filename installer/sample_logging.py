"""Optional diagnostics for sample-owned subprocesses; keep their return protocol."""

import json
import os
from pathlib import Path
import subprocess

from installer import diagnostics


def run(argv, **kwargs):
    executable = Path(argv[0]).name
    fields = {}
    try:
        supplied = json.loads(os.environ.get("BKN_SAMPLE_DIAGNOSTIC_CONTEXT", "{}"))
        fields = {key: supplied[key] for key in
                  ("sample_id", "version", "installation_id", "attempt_id", "operation")
                  if isinstance(supplied.get(key), str)}
    except (ValueError, TypeError, AttributeError):
        pass
    if executable == "openbkn":
        args = [item for item in argv[1:] if item != "--json"]
        details = diagnostics.command_details(args)
        phase = os.environ.get("BKN_SAMPLE_PHASE", "")
        if phase in {"dbInit", "dbVerify"}:
            stage = "database"
        elif phase == "platform-verify":
            stage = "verify"
        elif args and (args[0] in {"skill", "tool", "toolbox"} or args[:2] == ["bkn", "capability"]
                       or args[:2] == ["bkn", "object-metric"]
                       or args[0] == "call" and len(args) > 1 and "agent-operator-integration" in args[1]):
            stage = "capabilities"
        elif args and args[0] in {"vega", "resource"}:
            stage = "discover"
        else:
            stage = "knowledge"
        name = "cli." + details["command"].replace(" ", ".")
    else:
        # Python and shell wrappers expose only the script filename, never argv.
        script = Path(argv[1]).name if len(argv) > 1 else executable
        name, details, stage = "script." + script, {"executable": executable}, "platform-install"
    with diagnostics.context(**fields, stage=stage, source="sample"), \
            diagnostics.secrets([os.environ.get("BKN_TOKEN"), os.environ.get("MYSQL_PASSWORD")]), \
            diagnostics.step(name, **details) as outcome:
        result = subprocess.run(argv, **kwargs)
        outcome.update(ok=result.returncode == 0, returncode=result.returncode)
        if result.returncode:
            outcome["reason"] = diagnostics.command_failure(result)
        return result
