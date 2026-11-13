"""Run sample-authored hooks without the installer's OS identity or private files."""
import itertools
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from threading import Event, Lock, Thread
from installer import diagnostics

# Each invocation receives a different identity, including concurrent samples.
# Container restart terminates the old process tree before this counter restarts.
_ids = itertools.count(100000)
_lock = Lock()
_FILES = {'BKN_SAMPLE_INPUT': 'input.json', 'BKN_SAMPLE_OUTPUT': 'output.json',
          'BKN_SAMPLE_CONFIG': 'config.yaml', 'BKN_SAMPLE_RECEIPT': 'owned-execution.json'}
_ENV = {'PATH', 'LANG', 'LC_ALL', 'TZ', 'BKN_BASE_URL', 'BKN_TOKEN',
        'BKN_SAMPLE_ID', 'BKN_SAMPLE_VERSION', 'BKN_SAMPLE_EMBEDDING', 'EMBEDDING_MODEL_NAME',
        'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS', 'MYSQL_HOST', 'MYSQL_PORT',
        'MYSQL_DATABASE', 'MYSQL_ADMIN_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD'}
_LIMIT = 2 * 1024 * 1024
# How often the ownership receipt is mirrored to the installer's state while a hook runs.
RECEIPT_MIRROR_INTERVAL = 0.2


def _read_output(descriptor, name):
    """Read a hook-written regular file without following a hook-created symlink."""
    try:
        file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    except FileNotFoundError:
        return None
    with os.fdopen(file, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > _LIMIT:
            raise ValueError('invalid sample hook output')
        content = stream.read(_LIMIT + 1)
    if len(content) > _LIMIT:
        raise ValueError('sample hook output exceeds limit')
    return content


def _write_atomic(path, content):
    """Replace a state file in one step, so a killed service never leaves it truncated."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.hook-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _valid_receipt(content):
    try:
        receipt = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(receipt, dict) and all(
        isinstance(receipt.get(kind), list) and all(isinstance(id_, str) and id_ for id_ in receipt[kind])
        for kind in ('toolboxes', 'skills'))


class _ReceiptMirror:
    """Copy each complete ownership receipt to the state dir while the hook runs.

    The final copy-back runs in a ``finally`` of this process. If the service is
    killed (OOM, pod restart) that never happens, and a failed installation would
    have no receipt and could not be uninstalled. Mirroring keeps the latest
    receipt the hook itself wrote; it never invents one. Partially written or
    malformed snapshots are skipped and retried, never mirrored.
    """
    def __init__(self, descriptor, name, destination):
        self.descriptor, self.name, self.destination = descriptor, name, destination
        self.last = None
        self.stopped = Event()
        self.thread = Thread(target=self._loop, name='bkn-receipt-mirror', daemon=True)

    def poll(self):
        try:
            content = _read_output(self.descriptor, self.name)
        except (OSError, ValueError):
            return  # The final copy-back reports invalid outputs.
        if content is None or content == self.last or not _valid_receipt(content):
            return
        try:
            _write_atomic(self.destination, content)
        except OSError:
            return
        self.last = content

    def _loop(self):
        while not self.stopped.wait(RECEIPT_MIRROR_INTERVAL):
            self.poll()

    def __enter__(self):
        self.last = Path(self.destination).read_bytes() if Path(self.destination).is_file() else None
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stopped.set()
        self.thread.join()


def run_hook(sample_dir, script, run, environment, *, input_data=None):
    relative = script.relative_to(sample_dir)
    with _lock:
        uid = next(_ids)
    with tempfile.TemporaryDirectory(prefix='bkn-hook-') as temporary:
        root = Path(temporary)
        # Keep the outer directory root-owned: children cannot replace it in /tmp.
        root.chmod(0o711)
        sample = root / 'sample'
        shutil.copytree(sample_dir, sample, symlinks=False,
                        ignore=shutil.ignore_patterns('.*', '__pycache__', 'node_modules', 'bkn-eval', 'tests'))
        work = root / 'work'
        work.mkdir(mode=0o700)
        env = {key: value for key, value in environment.items() if key in _ENV}
        env.setdefault('PATH', os.environ.get('PATH', os.defpath))
        env.update(HOME=str(work), TMPDIR=str(work), PYTHONPATH='/opt/bkn-samples', PYTHONUNBUFFERED='1',
                   BKN_SAMPLE_CACHE=str(work / 'cache'), _BKN_HOOK_UID=str(uid),
                   BKN_SAMPLE_DIAGNOSTIC_CONTEXT=diagnostics.hook_context())
        if environment.get('BKN_SAMPLE_PHASE') in {'dbInit', 'dbVerify', 'platform-install', 'platform-verify'}:
            env['BKN_SAMPLE_PHASE'] = environment['BKN_SAMPLE_PHASE']
        for key, name in _FILES.items():
            if key not in environment:
                continue
            if key == 'BKN_SAMPLE_INPUT' and input_data is not None:
                env[key] = '/dev/stdin'
                env['_BKN_HOOK_INPUT'] = input_data
                continue
            env[key] = str(work / name)
            source = Path(environment[key])
            if key != 'BKN_SAMPLE_OUTPUT' and source.is_file():
                shutil.copyfile(source, work / name)
        # A mocked runner can be used in host unit tests. Real execution fails
        # closed in process_run unless Linux UID switching is available.
        if os.geteuid() == 0:
            for path in [sample, *sample.rglob('*'), work, *work.iterdir()]:
                os.chown(path, uid, uid)
        # Hold a directory descriptor before the hook runs. Copy back only known
        # regular outputs, without following a hook-created symlink or ancestor.
        descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
        try:
            mirror = None
            if 'BKN_SAMPLE_RECEIPT' in environment:
                mirror = _ReceiptMirror(descriptor, _FILES['BKN_SAMPLE_RECEIPT'], environment['BKN_SAMPLE_RECEIPT'])
            try:
                if mirror is None:
                    return run([str(sample / relative)], env)
                with mirror:
                    return run([str(sample / relative)], env)
            finally:
                for key, name in _FILES.items():
                    if key == 'BKN_SAMPLE_INPUT' or key not in environment:
                        continue
                    content = _read_output(descriptor, name)
                    if content is not None:
                        _write_atomic(environment[key], content)
        finally:
            os.close(descriptor)
