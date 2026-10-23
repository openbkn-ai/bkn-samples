"""Audited constraints for immutable releases whose manifests predate SDK requirements.

Keys identify reviewed manifest bytes, never sample names. This does not attest
server API availability: the original platform/capability checks still apply.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from threading import Lock

_CONSTRAINTS = json.loads(Path(__file__).with_suffix('.json').read_text())


class ExecutorCompatibilityError(ValueError):
    pass


def cli_capabilities(command, required_subcommands, *, timeout=5):
    # Hooks inherit this PATH through caller_env/run_hook. Resolve the same CLI,
    # not a host-specific path or a second separately installed SDK. No auth or
    # platform URL is necessary for --help; never include CLI stderr in errors.
    path = os.environ.get('PATH', os.defpath)
    executable = shutil.which('openbkn', path=path)
    if not executable:
        return False
    executable = str(Path(executable).resolve())
    with tempfile.TemporaryDirectory(prefix='bkn-cli-help-') as directory:
        env = {'PATH': path, 'HOME': directory, 'TMPDIR': directory,
               'LANG': os.environ.get('LANG', 'C.UTF-8')}
        try:
            result = subprocess.run([executable, *command, '--help'], env=env, cwd=directory,
                                    capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.SubprocessError, UnicodeError):
            return False
    # Commander may show parent help for an unknown command. Require the exact
    # command usage plus the expected operations, never exit status alone.
    text = result.stdout
    usage = r'^(?:Usage: |USAGE\r?\n  )' + ' '.join(re.escape(part) + r'(?:\|[a-zA-Z0-9_-]+)*' for part in ['openbkn', *command]) + r'(?:\s|\[|$)'
    return (result.returncode == 0 and re.search(usage, text, re.MULTILINE) is not None
            and all(re.search(r'^  ' + re.escape(name) + r'(?:\|[a-zA-Z0-9_-]+)*(?:[ \[<]|$)', text, re.MULTILINE)
                    for name in required_subcommands))


class ExecutorCompatibility:
    """One probe per immutable runtime instance, including failures (fail closed)."""
    def __init__(self):
        self._capabilities = {}
        self._lock = Lock()

    def require(self, entry):
        manifest = entry.get('manifest') if isinstance(entry, dict) else None
        if not isinstance(manifest, dict) or not isinstance(manifest.get('digest'), str):
            raise ExecutorCompatibilityError('Release manifest identity is invalid; installation is unavailable.')
        requirement = _CONSTRAINTS.get(manifest['digest'])
        if requirement is None:
            return
        deadline = time.monotonic() + 5
        for commands in requirement['commands']:
            key = (tuple(commands['command']), tuple(commands['subcommands']))
            with self._lock:
                if key not in self._capabilities:
                    remaining = deadline - time.monotonic()
                    self._capabilities[key] = remaining > 0 and cli_capabilities(*key, timeout=remaining)
                supported = self._capabilities[key]
            if not supported:
                command = ' '.join(['openbkn', *commands['command']])
                operations = ', '.join(commands['subcommands'])
                raise ExecutorCompatibilityError(
                    f"This fixed release requires '{command}' commands: {operations}, and "
                    f"{requirement['apiRequirement']}. This executor could not verify the required commands within the bounded offline probe. "
                    "Use a verified compatible executor/platform combination. Existing installations can still be uninstalled.")
