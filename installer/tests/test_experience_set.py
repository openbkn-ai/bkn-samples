import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from installer import experience_set
from installer.contract import discover_sample_dirs, load_sample, validate_document

ROOT = Path(__file__).resolve().parents[2]

CASE = {
    "id": "R-05",
    "title": "Products that use a material",
    "explanation": "Walks the BOM relations back from a material to products.",
    "question": "Which products use material 321-000569?",
    "answer": "Material 321-000569 is used by P61-000328 and P61-000351.",
    "expected": {"product_codes": ["P61-000328", "P61-000351"]},
    "surfaces": ["agent", "query"],
    "cypher": {"query": "MATCH (p:product) RETURN p.code AS product_codes"},
}
DOCUMENT = {
    "apiVersion": "samples.openbkn.ai/v1alpha1",
    "kind": "ExperienceSet",
    "metadata": {"language": "en-US", "source": {"answerSet": "bkn-eval/answers.yaml", "setId": "demo-v1"}},
    "spec": {"businessDate": "2026-08-25", "cases": [CASE]},
}


def document_with(**changes) -> dict:
    document = copy.deepcopy(DOCUMENT)
    document["spec"]["cases"][0].update(changes)
    return document


class RepositoryExperienceSetTest(unittest.TestCase):
    def test_every_declared_set_is_valid_and_matches_its_source(self):
        declared = 0
        for sample_dir in discover_sample_dirs(ROOT):
            sample = load_sample(sample_dir)
            relative = sample["spec"]["studio"].get("experienceSet")
            if relative is None:
                continue
            declared += 1
            document = experience_set.load(sample_dir / relative)
            with self.subTest(sample=sample_dir.name):
                self.assertEqual(experience_set.validate(document), [])
                self.assertEqual(experience_set.check_source(sample_dir, document), [])
                self.assertEqual(document["metadata"]["language"], sample["metadata"]["language"])
        self.assertGreaterEqual(declared, 2)


class ValidateTest(unittest.TestCase):
    def test_accepts_a_complete_case(self):
        self.assertEqual(experience_set.validate(DOCUMENT), [])

    def test_answer_must_name_every_expected_value(self):
        errors = experience_set.validate(document_with(answer="Material 321-000569 is used by P61-000328."))
        self.assertEqual(errors, ["R-05: answer does not name expected values ['P61-000351']"])

    def test_query_surface_needs_its_cypher(self):
        self.assertTrue(experience_set.validate(document_with(cypher={"graph": "MATCH (n) RETURN n"})))

    def test_graph_is_a_pattern_the_explorer_completes(self):
        pattern = "MATCH (p:product)-[:uses]->(m:material)\nWHERE m.code = '321-000569'"
        graph = dict(CASE["cypher"], graph=pattern)
        self.assertEqual(experience_set.validate(document_with(surfaces=["agent", "query", "graph"], cypher=graph)), [])
        graph["graph"] = pattern + "\nreturn p, m"
        self.assertTrue(experience_set.validate(document_with(surfaces=["agent", "query", "graph"], cypher=graph)))

    def test_cypher_without_its_surface_is_rejected(self):
        self.assertTrue(experience_set.validate(document_with(surfaces=["agent"])))

    def test_every_case_offers_the_agent(self):
        self.assertTrue(experience_set.validate(document_with(surfaces=["query"])))

    def test_duplicate_ids_are_rejected(self):
        document = copy.deepcopy(DOCUMENT)
        document["spec"]["cases"].append(copy.deepcopy(CASE))
        self.assertEqual(experience_set.validate(document), ["R-05: duplicate case id"])

    def test_answer_values_skip_flags_and_field_names(self):
        expected = {"covers": False, "leaf_shortages": {"606-000069": 41}, "fg_qty": 816.0, "usage": 1.5}
        self.assertEqual(experience_set.answer_values(expected), ["606-000069", "41", "816", "1.5"])


class CheckSourceTest(unittest.TestCase):
    def write_source(self, root: Path, answer: dict) -> None:
        source = {"set_id": "demo-v1", "business_date": "2026-08-25", "answers": [answer]}
        (root / "bkn-eval").mkdir()
        (root / "bkn-eval" / "answers.yaml").write_text(yaml.safe_dump(source), encoding="utf-8")

    def test_matching_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_source(root, {"id": "R-05", "question": CASE["question"], "expected": CASE["expected"]})
            self.assertEqual(experience_set.check_source(root, DOCUMENT), [])

    def test_drift_from_source_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_source(root, {"id": "R-05", "question": "Other?", "expected": {"product_codes": []}})
            self.assertEqual(experience_set.check_source(root, DOCUMENT), [
                "R-05: question differs from the source",
                "R-05: expected differs from the source",
            ])

    def test_missing_source_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(experience_set.check_source(Path(temporary), DOCUMENT),
                             ["source answer set is missing: bkn-eval/answers.yaml"])


class CompareQueryResultTest(unittest.TestCase):
    def test_scalars_compare_as_numbers(self):
        expected = {"count": 12, "qty": 20000}
        rows = [{"count": 12, "qty": "20000.000000"}]
        self.assertEqual(experience_set.compare_query_result(expected, ["count", "qty"], rows), [])

    def test_value_list_is_one_column_across_rows(self):
        expected = {"product_codes": ["P61-000351", "P61-000328"]}
        rows = [{"product_codes": "P61-000328"}, {"product_codes": "P61-000351"}]
        self.assertEqual(experience_set.compare_query_result(expected, ["product_codes"], rows), [])

    def test_record_list_is_the_rows(self):
        expected = {"substitutes": [{"material_code": "356-000356", "available_qty": 4673, "usage": 1}]}
        rows = [{"material_code": "356-000356", "available_qty": "4673.000000", "usage": "1.000000"}]
        columns = ["material_code", "available_qty", "usage"]
        self.assertEqual(experience_set.compare_query_result(expected, columns, rows), [])

    def test_differences_are_reported(self):
        self.assertEqual(experience_set.compare_query_result({"value": 534}, ["value"], [{"value": 533}]),
                         ["value: 533 differs from 534"])
        self.assertEqual(experience_set.compare_query_result({"value": 534}, ["total"], [{"total": 534}]),
                         ["result has no column value"])


class ContractTest(unittest.TestCase):
    def test_sample_contract_checks_the_declared_set(self):
        sample_dir = ROOT / "samples" / "supply_ontology_en"
        document = load_sample(sample_dir)
        self.assertEqual(validate_document(sample_dir, document), [])
        document["spec"]["studio"]["experienceSet"] = "experience/missing.yaml"
        self.assertIn("spec.studio.experienceSet does not exist: experience/missing.yaml",
                      validate_document(sample_dir, document))

    def test_set_language_must_match_the_sample(self):
        sample_dir = ROOT / "samples" / "supply_ontology_en"
        document = load_sample(sample_dir)
        document["metadata"]["language"] = "zh-CN"
        self.assertIn("spec.studio.experienceSet language must match metadata.language",
                      validate_document(sample_dir, document))


if __name__ == "__main__":
    unittest.main()
