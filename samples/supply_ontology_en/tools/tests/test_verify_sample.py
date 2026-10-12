from pathlib import Path

from verify_sample import verify


PACK = Path(__file__).parents[2]


def test_verify_sample_reports_all_release_gates():
    report = verify(PACK, run_tests=False)
    assert report["passed"] is True
    assert report["tests_passed"] is None
    assert report["evaluation"]["passed"] is True
    assert report["documentation_passed"] is True
