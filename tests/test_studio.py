import json
from pathlib import Path
import tempfile
import subprocess
import unittest
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'pipeline')]
import qa_glb
import validate_squat
import synthetic_squat
from test_qa import make_glb, clean_tracks


class TestRequiredValidation(unittest.TestCase):
    def test_missing_wrist_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.glb'
            make_glb(p, clean_tracks())
            p.write_bytes(p.read_bytes().replace(b'wrist.L', b'wrist_X'))
            results, _ = qa_glb.run_qa(p)
            self.assertFalse(qa_glb.summarise(results)['pass'])
            self.assertTrue(results[0]['critical'])
            self.assertIn('wrist.L', results[0]['detail'])

    def test_empty_animation_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'empty.glb'
            make_glb(p, {})
            results, _ = qa_glb.run_qa(p)
            self.assertFalse(qa_glb.summarise(results)['pass'])
            self.assertTrue(any(r['check'] == 'animation' and r['status'] == 'FAIL' for r in results))

    def test_missing_animation_array_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'empty.glb'
            make_glb(p, clean_tracks())
            p.write_bytes(p.read_bytes().replace(b'"animations"', b'"xnimations"'))
            results, _ = qa_glb.run_qa(p)
            self.assertFalse(qa_glb.summarise(results)['pass'])

    def test_missing_root_fails_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.glb'
            make_glb(p, clean_tracks())
            p.write_bytes(p.read_bytes().replace(b'"root"', b'"xxxx"'))
            results, _ = qa_glb.run_qa(p)
            self.assertFalse(qa_glb.summarise(results)['pass'])

    def test_stale_and_skipped_reports_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            make_glb(p/'squat-technical.glb',clean_tracks())
            for name in ('squat-technical.glb.gltf.json','strict-motion.json','preview.json','media.json','viewer-parity.json'):
                (p/name).write_text(json.dumps({'status':'SKIP','glb_sha256':'stale'}))
            report = validate_squat.aggregate(p)
            self.assertFalse(report['technical_pass'])
            for kind in ('gltf','strict','preview','media','parity'):
                self.assertIn(f'{kind}: missing or stale GLB hash',report['errors'])
                self.assertIn(f'{kind}: required check did not pass',report['errors'])

    def test_required_check_cannot_be_skipped_or_removed(self):
        rows = [dict(check=c, joint=j, status='PASS') for c, j in validate_squat.required_qa()]
        report = dict(results=rows, summary={'pass': True})
        self.assertTrue(validate_squat.audit_qa(report)[0])
        for index in range(len(rows)):
            changed = [dict(r) for r in rows]
            changed[index]['status'] = 'SKIP'
            self.assertFalse(validate_squat.audit_qa(dict(report, results=changed))[0])
            self.assertFalse(validate_squat.audit_qa(dict(report, results=rows[:index]+rows[index+1:]))[0])

    def test_missing_reports_fail_even_with_glb(self):
        with tempfile.TemporaryDirectory() as d:
            make_glb(Path(d) / 'squat-technical.glb', clean_tracks())
            report = validate_squat.aggregate(d)
            self.assertFalse(report['technical_pass'])
            for name in ('qa', 'gltf', 'strict', 'preview', 'media'):
                self.assertIn(f'{name}: missing or invalid report', report['errors'])

    def test_failed_cli_revalidation_invalidates_old_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'validation.json'
            p.write_text(json.dumps({'technical_pass':True}))
            proc = subprocess.run([sys.executable,validate_squat.__file__,d],capture_output=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertFalse(json.loads(p.read_text())['technical_pass'])

    def test_synthetic_provenance_and_closed_endpoint(self):
        motion = synthetic_squat.generate()
        self.assertEqual(motion['source']['kind'], 'synthetic')
        self.assertEqual(motion['license'], 'MIT')
        self.assertTrue(motion['technical_preview'])
        self.assertEqual(motion['frames'][0], motion['frames'][-1])


if __name__ == '__main__':
    unittest.main()
