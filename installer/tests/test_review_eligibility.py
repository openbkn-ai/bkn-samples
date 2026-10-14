"""Release-branch review keeps the trusted same-repository and freshness guards."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('sample_review', ROOT / '.github/scripts/deepseek_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
REPO = 'openbkn-ai/bkn-samples'


class ReviewEligibilityTest(unittest.TestCase):
    def metadata(self, branch):
        return {'state': 'open', 'draft': False, 'base': {'ref': branch, 'sha': 'b' * 40},
                'head': {'sha': 'a' * 40, 'repo': {'full_name': REPO}}}

    def test_only_main_and_020_same_repo_ready_prs_are_reviewable(self):
        for branch in ['main', 'release/0.2.0']:
            value = self.metadata(branch)
            self.assertTrue(review.reviewable(value, REPO))
            for field, changed in [('draft', True), ('state', 'closed')]:
                self.assertFalse(review.reviewable({**value, field: changed}, REPO))
            foreign = copy.deepcopy(value)
            foreign['head']['repo']['full_name'] = 'other/samples'
            self.assertFalse(review.reviewable(foreign, REPO))
        for branch in ['release/0.2.1', 'release/0.2.0/other', 'feature/test']:
            self.assertFalse(review.reviewable(self.metadata(branch), REPO))

    def test_status_accepts_020_but_rejects_stale_or_unsupported_targets(self):
        env = {'GH_REPO': REPO, 'PR_NUMBER': '144', 'REVIEW_HEAD': 'a' * 40,
               'REVIEW_BASE': 'b' * 40, 'REVIEW_DECISION': 'success'}
        for branch, base, expected in [('release/0.2.0', 'b' * 40, 'success'),
                                       ('release/0.2.0', 'c' * 40, 'error'),
                                       ('feature/test', 'b' * 40, 'error')]:
            value = self.metadata(branch)
            value['base']['sha'] = base
            with patch.dict('os.environ', env), patch.object(review, 'api', return_value=value), \
                 patch.object(review, 'publish_status') as publish:
                review.status()
            self.assertEqual(publish.call_args.args[2], expected)
