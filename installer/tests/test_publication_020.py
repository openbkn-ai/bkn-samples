"""Original020 compatibility must not silently inherit a newer install protocol."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('build_candidate_020', ROOT / 'tools/publication/build_candidate_020.py')


def load():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def test_pinned_legacy_builder_narrows_only_platform_constraint():
    module = load()
    source = module.read_legacy_source(ROOT)
    transformed = module.compatible_source(source)
    original = b'"platformVersion": ">=0.2.0 <0.3.0"'
    replacement = b'"platformVersion": ">=0.2.0 <0.2.1"'
    assert hashlib.sha256(source).hexdigest() == module.LEGACY_SHA256
    assert transformed == source.replace(original, replacement)
    assert b'samples.openbkn.ai/offline.v1' in transformed
    assert transformed.count(replacement) == 1


def test_rejects_tampered_builder():
    module = load()
    source = module.read_legacy_source(ROOT)
    with pytest.raises(ValueError, match='digest'):
        module.compatible_source(source + b'\n')


def test_compatibility_builder_uses_current_source_root():
    module = load()
    legacy = module.load_legacy(ROOT)
    assert legacy['ROOT'] == ROOT
    assert legacy['included'](Path('tools/fn/allocation.py'))
    assert not legacy['included'](Path('bkn-eval/datasets/sample-answer-set-v1.yaml'))
    assert not legacy['included'](Path('experience/experience-set.yaml'))


def test_untracked_runtime_file_cannot_be_silently_omitted(tmp_path, monkeypatch):
    import subprocess
    module = load()
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    sample = tmp_path / 'samples/supply_ontology_hand'
    sample.mkdir(parents=True)
    (sample / 'allocation.py').write_text('new runtime code')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='stage all new sample files'):
        module.build(sample, '0.1.16', tmp_path / 'out', 'image@sha256:' + '0' * 64, allow_dirty=True)


def test_final_build_rejects_staged_but_uncommitted_source(tmp_path, monkeypatch):
    import subprocess
    module = load()
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    sample = tmp_path / 'samples/supply_ontology_hand'
    sample.mkdir(parents=True)
    (sample / 'allocation.py').write_text('new runtime code')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='clean source commit'):
        module.build(sample, '0.1.16', tmp_path / 'out', 'image@sha256:' + '0' * 64)
