"""Research metadata must not silently promote uninspected or mismatched evidence."""
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

LIBRARY = Path(__file__).resolve().parents[1] / 'reference-library'
BUILD = runpy.run_path(str(LIBRARY / 'tools' / 'build.py'))
VALIDATE = runpy.run_path(str(LIBRARY / 'tools' / 'validate.py'))['validate']


class ResearchEvidenceContracts(unittest.TestCase):
    def test_negative_wording_is_not_visual_inspection(self):
        check = BUILD['is_visually_inspected']
        self.assertFalse(check({'verification': 'not_visually_inspected'}))
        self.assertFalse(check({'verification': 'page_text'}))
        self.assertTrue(check({'verification': 'visually_inspected_sampled_frames', 'visual_inspected': True}))
        with self.assertRaises(ValueError):
            check({'verification': 'page_text', 'visual_inspected': True})
        with self.assertRaises(ValueError):
            check({'verification': 'visually_inspected', 'visual_inspected': 'false'})

    def _mutated_errors(self, filename, mutate):
        with tempfile.TemporaryDirectory(prefix='fms-reference-test-') as tmp:
            target = Path(tmp)
            shutil.copytree(LIBRARY / 'data', target / 'data')
            path = target / 'data' / filename
            records = json.loads(path.read_text(encoding='utf-8'))
            mutate(records)
            path.write_text(json.dumps(records), encoding='utf-8')
            return VALIDATE(target)

    def test_unresolved_equipment_alternative_is_rejected(self):
        errors = self._mutated_errors('exercise-variations.json', lambda rows: next(v for v in rows if v['id'] == 'dumbbell-goblet-head-support').update(reference_status='research_required'))
        self.assertTrue(any('unresolved variation' in e for e in errors), errors)

    def test_missing_alternative_member_is_rejected(self):
        errors = self._mutated_errors('equipment-alternative-groups.json', lambda rows: rows[0]['variation_ids'].append('nonexistent-squat'))
        self.assertTrue(any('unknown alternative member' in e for e in errors), errors)

    def test_mismatched_source_is_rejected(self):
        errors = self._mutated_errors('references.json', lambda rows: rows[0].update(source_url='https://example.com/incorrect-variation'))
        self.assertTrue(any('source' in e and 'mismatch' in e for e in errors), errors)

    def test_current_research_relationships(self):
        self.assertEqual([], VALIDATE())

    def test_generated_local_path_must_match_manifest(self):
        errors = self._mutated_errors('references.json', lambda rows: next(r for r in rows if r.get('local_path')).update(local_path='C:/outside/nonexistent.jpg', local_sha256='0' * 64))
        self.assertTrue(any('local manifest mismatch for local_path' in e for e in errors), errors)
        self.assertTrue(any('local manifest mismatch for local_sha256' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
