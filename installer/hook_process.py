"""Run sample-authored hooks without the installer's OS identity or private files."""
import itertools
import os
import shutil
import stat
import tempfile
from pathlib import Path
from threading import Lock

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
        env.update(HOME=str(work), TMPDIR=str(work), PYTHONPATH='/opt/bkn-samples',
                   BKN_SAMPLE_CACHE=str(work / 'cache'), _BKN_HOOK_UID=str(uid))
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
            try:
                return run([str(sample / relative)], env)
            finally:
                for key, name in _FILES.items():
                    if key == 'BKN_SAMPLE_INPUT' or key not in environment:
                        continue
                    try:
                        file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
                    except FileNotFoundError:
                        continue
                    with os.fdopen(file, 'rb') as stream:
                        info = os.fstat(stream.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_size > _LIMIT:
                            raise ValueError('invalid sample hook output')
                        content = stream.read(_LIMIT + 1)
                    if len(content) > _LIMIT:
                        raise ValueError('sample hook output exceeds limit')
                    Path(environment[key]).write_bytes(content)
        finally:
            os.close(descriptor)
