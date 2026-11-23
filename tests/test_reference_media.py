"""Local downloads must not masquerade as media or approved visual evidence."""
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'reference-library/tools/cache_media.py'))


class LocalReferenceMediaTests(unittest.TestCase):
    def test_error_page_is_not_media(self):
        with self.assertRaises(ValueError):
            MODULE['media_kind'](b'<!DOCTYPE html><title>Access denied</title>')
        self.assertEqual('.gif', MODULE['media_kind'](b'GIF89aexample'))

    def test_player_and_restricted_sources_are_not_download_candidates(self):
        for url, status in [('https://www.youtube.com/watch?v=x', 'external_player'),
                            ('https://assets.nhs.uk/example.jpg', 'source_restriction')]:
            self.assertEqual(status, MODULE['candidate']({'media_url': url, 'source_url': 'https://example.org/'})[1])

    def test_origin_fallback_is_narrow(self):
        f = MODULE['publisher_origin']
        self.assertEqual('https://www.strengthlog.com/wp-content/uploads/example.gif', f('https://i0.wp.com/www.strengthlog.com/wp-content/uploads/example.gif?resize=600'))
        self.assertIsNone(f('https://i0.wp.com/other.example/private.gif'))
        self.assertIsNone(f('https://untrusted.example/www.strengthlog.com/wp-content/uploads/x.gif'))

    def test_corrupt_cache_is_not_reused(self):
        fetch = MODULE['fetch']
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cache = repo / 'work/reference-media'
            cache.mkdir(parents=True)
            target = cache / 'broken.gif'
            target.write_bytes(b'corrupt')
            with patch.dict(fetch.__globals__, REPO=repo, CACHE=cache), patch.dict(fetch.__globals__, urlopen=lambda *a, **k: (_ for _ in ()).throw(OSError('offline'))):
                result = fetch('https://example.org/x.gif', {'local_path': 'work/reference-media/broken.gif', 'sha256': '0' * 64})
            self.assertEqual('download_failed', result['status'])
            self.assertNotIn('local_path', result)

    def test_preview_keeps_distinct_frames_without_claiming_inspection(self):
        from PIL import Image
        preview = MODULE['make_preview']
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cache = repo / 'work/reference-media'
            cache.mkdir(parents=True)
            target = cache / 'sample.gif'
            images = [Image.new('RGB', (20, 20), c) for c in ['red', 'green', 'blue']]
            images[0].save(target, save_all=True, append_images=images[1:], duration=100)
            with patch.dict(preview.__globals__, REPO=repo, CACHE=cache):
                result = preview(target)
            self.assertEqual([0, 1, 2], [x['frame_index'] for x in result['preview_samples']])
            with Image.open(repo / result['preview_path']) as output:
                self.assertNotEqual(output.getpixel((5, 30)), output.getpixel((325, 30)))
            self.assertNotIn('visual_inspected', result)

    def test_reuse_preserves_original_retrieval_provenance(self):
        fetch = MODULE['fetch']
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            cache = repo / 'work/reference-media'
            cache.mkdir(parents=True)
            target = cache / 'example.pdf'
            target.write_bytes(b'%PDF-original')
            previous = {'local_path': 'work/reference-media/example.pdf', 'sha256': MODULE['digest'](target.read_bytes()),
                        'downloaded_at': '2026-11-23T00:00:00+00:00', 'retrieval_note': 'Original CDN fallback'}
            with patch.dict(fetch.__globals__, REPO=repo, CACHE=cache), patch.dict(fetch.__globals__, urlopen=lambda *a, **k: self.fail('Cache hit must not download')):
                result = fetch('https://example.org/example.pdf', previous)
            self.assertEqual('cached', result['status'])
            self.assertEqual(previous['downloaded_at'], result['downloaded_at'])
            self.assertEqual(previous['retrieval_note'], result['retrieval_note'])
            self.assertNotEqual(result['downloaded_at'], result['checked_at'])


if __name__ == '__main__':
    unittest.main()
