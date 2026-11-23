"""Cache catalogued public media for local research, never for publication.

Run after build.py, then rebuild to expose local paths. No page scraping,
stream extraction, authentication, or access-control bypass is performed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

LIBRARY = Path(__file__).resolve().parents[1]
REPO = LIBRARY.parent
CACHE = REPO / 'work/reference-media'
MAX_BYTES = 80 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publisher_origin(url):
    """WordPress image CDN embeds the original public URL in its path."""
    parsed = urlsplit(url)
    if parsed.hostname in {'i0.wp.com', 'i1.wp.com', 'i2.wp.com'} and parsed.path.startswith('/www.strengthlog.com/wp-content/uploads/'):
        return 'https:/' + parsed.path
    return None


def media_kind(data):
    """Reject HTML/error bodies even when the URL ends in a media suffix."""
    if data.startswith((b'GIF87a', b'GIF89a')):
        return '.gif'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return '.webp'
    if data.startswith(b'%PDF-'):
        return '.pdf'
    if data[4:8] == b'ftyp':
        return '.mp4'
    raise ValueError('Response is not a recognized image, PDF or MP4')


def candidate(ref):
    url = ref.get('media_url')
    if not url and urlsplit(ref['source_url']).path.lower().endswith('.pdf'):
        url = ref['source_url']
    if not url:
        return None, 'no_direct_media', 'Source page has no catalogued downloadable media.'
    url = urldefrag(url)[0]
    host = urlsplit(url).hostname or ''
    if host in {'youtube.com', 'www.youtube.com', 'youtu.be', 'vimeo.com', 'www.vimeo.com'}:
        return url, 'external_player', 'Player page, not a direct media file; no stream extraction.'
    if host == 'assets.nhs.uk':
        return url, 'source_restriction', 'NHS terms 3.5 exclude identifiable-person images from the general reuse grant; permission unresolved.'
    if urlsplit(url).scheme != 'https':
        return url, 'unsupported_url', 'Only catalogued public HTTPS media is eligible.'
    return url, None, None


def make_preview(path):
    """Mechanical frame samples, not a visual inspection or a phase map."""
    from PIL import Image, ImageDraw
    with Image.open(path) as im:
        count = getattr(im, 'n_frames', 1)
        if count > 2000 or im.width * im.height > 25_000_000:
            raise ValueError('Image exceeds preview resource limits')
        selected = sorted({round(i * (count - 1) / 5) for i in range(6)})
        canvas = Image.new('RGB', (960, 350 * ((len(selected) + 2) // 3)), 'white')
        draw = ImageDraw.Draw(canvas)
        frames = []
        for n, index in enumerate(selected):
            im.seek(index)
            frame = im.convert('RGB').copy()
            frame.thumbnail((312, 312))
            x, y = (n % 3) * 320, (n // 3) * 350
            canvas.paste(frame, (x, y + 25))
            draw.text((x + 4, y + 5), f'Frame {index} / {count - 1}', fill='black')
            frames.append({'frame_index': index, 'duration_ms': im.info.get('duration')})
        target = CACHE / 'previews' / (path.stem + '.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target)
    return {'preview_path': target.relative_to(REPO).as_posix(),
            'preview_sha256': digest(target.read_bytes()), 'frame_count': count,
            'preview_samples': frames,
            'preview_basis': 'Evenly spaced frame indices; not semantic phases or movement approval.'}


def fetch(url, previous):
    result = {'download_url': url, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'rights': 'Private internal reference cache requested by user; no redistribution or production-use grant implied.'}
    try:
        old_path = REPO / previous.get('local_path', 'missing')
        # Never read paths outside the dedicated cache from a prior manifest.
        if old_path.resolve().is_relative_to(CACHE.resolve()) and old_path.is_file() and digest(old_path.read_bytes()) == previous.get('sha256'):
            result.update({k: v for k, v in previous.items() if k in {'local_path', 'sha256', 'bytes', 'content_type', 'resolved_url', 'retrieval_note'}})
            result['downloaded_at'] = previous.get('downloaded_at', previous.get('checked_at'))
        else:
            req = Request(url, headers={'User-Agent': 'ForgedMotionStudio-InternalReference/1.0'})
            try:
                response = urlopen(req, timeout=25)
            except HTTPError as exc:
                original = publisher_origin(url)
                if exc.code != 404 or not original:
                    raise
                result['retrieval_note'] = 'CDN returned 404; retrieved original public asset URL embedded in CDN path.'
                response = urlopen(Request(original, headers={'User-Agent': 'ForgedMotionStudio-InternalReference/1.0'}), timeout=25)
            with response:
                if urlsplit(response.url).scheme != 'https':
                    raise ValueError('Non-HTTPS redirect rejected')
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError('Media exceeds 80 MiB limit')
                suffix = media_kind(data)
                sha = digest(data)
                target = CACHE / 'assets' / (sha + suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                result.update(local_path=target.relative_to(REPO).as_posix(), sha256=sha,
                              bytes=len(data), content_type=response.headers.get('Content-Type'),
                              resolved_url=response.url, downloaded_at=result['checked_at'])
        result['status'] = 'cached'
        if Path(result['local_path']).suffix in {'.gif', '.jpg', '.png', '.webp'}:
            try:
                result.update(make_preview(REPO / result['local_path']))
            except Exception as exc:
                result['preview_error'] = str(exc)
    except Exception as exc:
        result.update(status='download_failed', error=f'{type(exc).__name__}: {exc}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    refs = json.loads((LIBRARY / 'data/references.json').read_text(encoding='utf-8'))
    manifest_path = LIBRARY / 'data/local-media.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    prior_urls = {r['download_url']: r for r in previous if r.get('status') == 'cached'}
    jobs, records = {}, []
    for ref in refs:
        url, status, reason = candidate(ref)
        record = {'reference_id': ref['id'], 'owner_id': ref['owner_id'],
                  'source_url': ref['source_url'], 'media_url': ref.get('media_url'),
                  'organization': ref['organization'], 'download_url': url}
        if status:
            record.update(status=status, reason=reason)
        else:
            jobs[url] = None
        records.append(record)
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        futures = {pool.submit(fetch, url, prior_urls.get(url, {})): url for url in jobs}
        for future in as_completed(futures):
            url = futures[future]
            jobs[url] = future.result()
            print(f'{len([v for v in jobs.values() if v])}/{len(jobs)} {jobs[url]["status"]}: {url}', flush=True)
    for record in records:
        if 'status' not in record:
            record.update(jobs[record['download_url']])
    manifest_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    # Self-contained local lookup; no downloaded bytes go into Git-ready research folders.
    (CACHE / 'manifest.json').write_text(manifest_path.read_text(encoding='utf-8'), encoding='utf-8')
    lines = ['# Local exercise media', '', 'Internal reference only; preserve source attribution. Downloading and automatic previews do not imply visual inspection.', '']
    for r in records:
        lines += [f'## {r["owner_id"]} — {r["reference_id"]}', '', f'[{r["organization"]} source]({r["source_url"]}) · {r["status"]}', '']
        if r.get('local_path'):
            local = Path(r['local_path']).relative_to('work/reference-media').as_posix()
            lines += [f'[Original media]({local})', '']
            if r.get('preview_path'):
                preview = Path(r['preview_path']).relative_to('work/reference-media').as_posix()
                lines += [f'![Automatic frame samples; not phase verification]({preview})', '']
        else:
            lines += [r.get('reason', r.get('error', 'Unresolved')), '']
    (CACHE / 'INDEX.md').write_text('\n'.join(lines), encoding='utf-8')
    from collections import Counter
    print(json.dumps(dict(Counter(r['status'] for r in records)), indent=2))


if __name__ == '__main__':
    main()
