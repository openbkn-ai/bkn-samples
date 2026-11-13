"""Hook file/environment boundaries; Linux root test checks actual UID separation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from installer import hook_process
from installer.hook_process import run_hook
from installer.tests.killed_hook import kill_during_hook
from installer.runtime import process_run


class HookProcessTest(unittest.TestCase):
    def test_environment_is_allowlisted_and_outputs_return_to_private_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sample = root / 'sample'
            sample.mkdir()
            script = sample / 'hook.sh'
            script.write_text('#!/bin/sh\nexit 0\n')
            output = root / 'output.json'
            receipt = root / 'receipt.json'
            receipt.write_text('{"skills": []}')
            identities = []
            def fake_run(argv, env):
                self.assertNotIn('BKN_SAMPLE_DB_PASSWORD_FILE', env)
                self.assertNotIn('KUBECONFIG', env)
                self.assertNotIn('AWS_SECRET_ACCESS_KEY', env)
                self.assertEqual(env['BKN_TOKEN'], 'current-caller')
                self.assertNotEqual(argv[0], str(script))
                self.assertEqual(json.loads(Path(env['BKN_SAMPLE_RECEIPT']).read_text()), {'skills': []})
                identities.append(env['_BKN_HOOK_UID'])
                Path(env['BKN_SAMPLE_OUTPUT']).write_text('{"ok": true}')
                return subprocess.CompletedProcess(argv, 0)
            environment = {'BKN_SAMPLE_DB_PASSWORD_FILE': '/private/admin', 'KUBECONFIG': '/private/config',
                           'AWS_SECRET_ACCESS_KEY': 'private', 'BKN_TOKEN': 'current-caller',
                           'BKN_SAMPLE_OUTPUT': str(output), 'BKN_SAMPLE_RECEIPT': str(receipt)}
            for _ in range(2):
                run_hook(sample, script, fake_run, environment)
                self.assertEqual(json.loads(output.read_text()), {'ok': True})
            self.assertNotEqual(*identities)

    def test_output_symlinks_cannot_copy_installer_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sample = root / 'sample'; sample.mkdir()
            script = sample / 'hook.sh'; script.write_text('')
            secret = root / 'admin'; secret.write_text('private')
            output = root / 'output.json'
            def malicious(argv, env):
                Path(env['BKN_SAMPLE_OUTPUT']).symlink_to(secret)
                return subprocess.CompletedProcess(argv, 0)
            with self.assertRaises(OSError):
                run_hook(sample, script, malicious, {'BKN_SAMPLE_OUTPUT': str(output)})
            self.assertFalse(output.exists())

    def test_killed_service_keeps_latest_receipt_written_by_the_hook(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / 'state' / 'manufacturing' / 'owned-execution.json'
            empty = json.dumps({'toolboxes': [], 'skills': []})
            latest = json.dumps({'toolboxes': ['box-1'], 'skills': ['skill-1']})
            output = kill_during_hook(receipt, root, [empty, latest])
            # The killed process never ran its copy-back of other outputs ...
            self.assertFalse(output.exists())
            # ... but the receipt reached the state directory as the hook last wrote it.
            self.assertEqual(json.loads(receipt.read_text()), {'toolboxes': ['box-1'], 'skills': ['skill-1']})
            self.assertEqual([path.name for path in receipt.parent.iterdir()], ['owned-execution.json'])

    def test_killed_service_without_hook_receipt_leaves_no_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / 'state' / 'owned-execution.json'
            kill_during_hook(receipt, root, [])
            self.assertFalse(receipt.exists())

    def test_mirror_skips_partial_or_invalid_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / 'work'; work.mkdir()
            destination = root / 'owned-execution.json'
            destination.write_text('{"toolboxes": [], "skills": ["previous"]}')
            descriptor = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
            try:
                mirror = hook_process._ReceiptMirror(descriptor, 'owned-execution.json', destination)
                mirror.last = destination.read_bytes()
                for content in ('{"toolboxes": [', '[]', '{"toolboxes": [], "skills": [7]}', '{"skills": []}'):
                    (work / 'owned-execution.json').write_text(content)
                    mirror.poll()
                    self.assertEqual(json.loads(destination.read_text()), {'toolboxes': [], 'skills': ['previous']})
                (work / 'owned-execution.json').unlink()
                (work / 'owned-execution.json').symlink_to(root / 'elsewhere.json')
                (root / 'elsewhere.json').write_text('{"toolboxes": ["foreign"], "skills": []}')
                mirror.poll()
                self.assertEqual(json.loads(destination.read_text()), {'toolboxes': [], 'skills': ['previous']})
                (work / 'owned-execution.json').unlink()
                (work / 'owned-execution.json').write_text('{"toolboxes": ["box"], "skills": []}')
                mirror.poll()
                self.assertEqual(json.loads(destination.read_text()), {'toolboxes': ['box'], 'skills': []})
            finally:
                os.close(descriptor)

    def test_completed_hook_still_copies_final_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sample = root / 'sample'; sample.mkdir()
            script = sample / 'hook.sh'; script.write_text('')
            receipt = root / 'owned-execution.json'
            def hook(argv, env):
                Path(env['BKN_SAMPLE_RECEIPT']).write_text('{"toolboxes": [], "skills": ["final"]}')
                return subprocess.CompletedProcess(argv, 1)
            run_hook(sample, script, hook, {'BKN_SAMPLE_RECEIPT': str(receipt)})
            self.assertEqual(json.loads(receipt.read_text()), {'toolboxes': [], 'skills': ['final']})

    @unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'requires the Linux product runtime')
    def test_real_hook_cannot_read_root_secret_or_parent_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o711)
            secret = root / 'admin-password'; secret.write_text('must-stay-private'); secret.chmod(0o400)
            sample = root / 'sample'; sample.mkdir()
            script = sample / 'probe.py'
            script.write_text('''#!/usr/local/bin/python3
import json, os
from pathlib import Path
blocked = []
for path in (''' + repr(str(secret)) + ''', '/proc/%s/environ' % os.getppid()):
    try:
        Path(path).read_bytes()
        blocked.append(False)
    except PermissionError:
        blocked.append(True)
assert '_BKN_HOOK_INPUT' not in os.environ
assert json.loads(Path(os.environ['BKN_SAMPLE_INPUT']).read_text()) == {'currentSample': 'scoped'}
status = Path('/proc/self/status').read_text()
Path(os.environ['BKN_SAMPLE_OUTPUT']).write_text(json.dumps({'uid': os.geteuid(), 'groups': os.getgroups(), 'blocked': blocked, 'zeroCaps': 'CapEff:\\t0000000000000000' in status, 'noNewPrivileges': 'NoNewPrivs:\\t1' in status}))
''')
            script.chmod(0o755)
            output = root / 'output.json'
            result = run_hook(sample, script, process_run, {'BKN_SAMPLE_OUTPUT': str(output), 'BKN_SAMPLE_INPUT': '/dev/stdin'}, input_data=json.dumps({'currentSample': 'scoped'}))
            self.assertEqual(result.returncode, 0, result.stderr)
            proof = json.loads(output.read_text())
            self.assertNotEqual(proof['uid'], 0)
            self.assertEqual(proof['groups'], [])
            self.assertEqual(proof['blocked'], [True, True])
            self.assertTrue(proof['zeroCaps'])
            self.assertTrue(proof['noNewPrivileges'])
