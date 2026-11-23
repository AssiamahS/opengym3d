"""Fail on invalid research relationships; does not certify remote media or technique."""
import json
import re
import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT, local_media=False):
    errors = []
    data = {}
    names = ['exercise-families', 'exercise-variations', 'equipment', 'equipment-configurations', 'equipment-alternative-groups', 'grip-archetypes', 'references', 'sources']
    for name in names:
        records = json.loads((root / 'data' / (name + '.json')).read_text(encoding='utf-8'))
        ids = [r['id'] for r in records]
        if len(set(ids)) != len(ids):
            errors.append(f'{name}: duplicate ID')
        if not all(re.fullmatch(r'[a-z0-9][a-z0-9.-]*', id_) for id_ in ids):
            errors.append(f'{name}: invalid ID')
        data[name] = {r['id']: r for r in records}
    def require(condition, message):
        if not condition:
            errors.append(message)
    variations, refs = data['exercise-variations'], data['references']
    for id_, v in variations.items():
        required = ['family', 'name', 'equipment', 'grip_id', 'source_urls', 'reference_ids', 'movement', 'movement_phases', 'missing_evidence', 'confidence', 'review_status', 'reference_status', 'equipment_configuration_ids', 'source_conflicts', 'equipment_alternative_group_ids']
        require(all(k in v for k in required), f'{id_}: required fields')
        require(v['family'] in data['exercise-families'], f'{id_}: family missing')
        require(v['grip_id'] in data['grip-archetypes'], f'{id_}: grip missing')
        require(v['review_status'] == 'unreviewed', f'{id_}: unexpected approval')
        require(v['reference_status'] in ['partial', 'research_required'], f'{id_}: unjustified completion')
        require(bool(v['source_urls']) and bool(v['reference_ids']), f'{id_}: no source evidence')
        require(all(e in data['equipment'] for e in v['equipment']), f'{id_}: unknown equipment')
        require(id_ in data['exercise-families'][v['family']]['variation_ids'], f'{id_}: family backlink')
        require(id_ in data['grip-archetypes'][v['grip_id']]['variation_ids'], f'{id_}: grip backlink')
        for rid in v['reference_ids']:
            require(rid in refs, f'{id_}: missing reference {rid}')
            if rid in refs:
                require(refs[rid]['owner_id'] == id_ and refs[rid]['owner_type'] == 'variation', f'{id_}: reference owner mismatch')
                require(refs[rid]['source_url'] in v['source_urls'], f'{id_}: source correspondence mismatch')
        for cid in v['equipment_configuration_ids']:
            c = data['equipment-configurations'].get(cid)
            require(c is not None and c['variation_id'] == id_ and c['equipment_id'] in v['equipment'], f'{id_}: configuration mismatch')
        for gid in v.get('equipment_alternative_group_ids', []):
            g = data['equipment-alternative-groups'].get(gid)
            require(g is not None and id_ in g['variation_ids'], f'{id_}: alternative-group backlink mismatch')
        phase_ids = [p['id'] for p in v['movement_phases']]
        require(len(phase_ids) == len(set(phase_ids)), f'{id_}: duplicate phase ID')
    for gid, g in data['equipment-alternative-groups'].items():
        members = g['variation_ids']
        require(len(members) >= 2 and len(members) == len(set(members)), f'{gid}: alternative group needs distinct members')
        require(all(k in g for k in ['selection_context', 'shared_intent', 'differences', 'not_implied', 'basis', 'review_status']), f'{gid}: alternative context missing')
        for vid in members:
            v = variations.get(vid)
            require(v is not None, f'{gid}: unknown alternative member {vid}')
            if v:
                require(gid in v.get('equipment_alternative_group_ids', []), f'{gid}: alternative backlink missing')
                require(v['reference_status'] != 'research_required', f'{gid}: unresolved variation cannot be an available alternative')
        equipment_sets = {tuple(sorted(variations[vid]['equipment'])) for vid in members if vid in variations}
        require(len(equipment_sets) >= 2, f'{gid}: no distinct equipment choices')
    for rid, r in refs.items():
        require(all(k in r for k in ['source_id', 'source_url', 'media_url', 'type', 'view', 'phase', 'description', 'verification', 'organization', 'access_date', 'rights', 'visual_inspected']), f'{rid}: reference fields missing')
        require(r['source_id'] in data['sources'] and data['sources'][r['source_id']]['url'] == r['source_url'], f'{rid}: source mismatch')
        owners = variations if r['owner_type'] == 'variation' else data['grip-archetypes']
        require(r['owner_id'] in owners, f'{rid}: orphan reference')
        for url in [r['source_url'], r['media_url']]:
            if url is not None:
                require(urlsplit(url).scheme == 'https' and bool(urlsplit(url).netloc), f'{rid}: invalid URL')
        if r['visual_inspected']:
            require(bool(r['media_url']) and r['view'] is not None, f'{rid}: inspected visual lacks media or view')
        require(isinstance(r['visual_inspected'], bool), f'{rid}: inspection flag must be boolean')
        for sample in r.get('observed_samples', []):
            require(all(k in sample for k in ['locator', 'view', 'phase', 'observation', 'limitations']), f'{rid}: incomplete sample provenance')
        require(not r.get('full_cycle_reviewed', False), f'{rid}: full-cycle review not established in current batches')
    for name in ['equipment', 'equipment-configurations', 'equipment-alternative-groups', 'grip-archetypes']:
        require(all(r['review_status'] == 'unreviewed' for r in data[name].values()), f'{name}: unexpected approval')
    for f in root.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', f.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (f.parent / unquote(target.split('#')[0])).resolve()
            optional_cache = resolved.is_relative_to((root.parent / 'work/reference-media').resolve())
            if local_media or not optional_cache:
                require(resolved.exists(), f'{f.relative_to(root)}: broken relative link {target}')
    coverage = json.loads((root / 'data/coverage.json').read_text())
    require(coverage['exercise-variations'] == len(variations), 'stale variation coverage')
    require(coverage['references'] == len(refs), 'stale reference coverage')
    require(coverage['partial_variations'] == sum(v['reference_status'] == 'partial' for v in variations.values()), 'stale partial coverage')
    require(coverage['research_required_variations'] == sum(v['reference_status'] == 'research_required' for v in variations.values()), 'stale research-required coverage')
    require(coverage['variations_with_visual_inspection'] == sum(any(refs[r]['visual_inspected'] for r in v['reference_ids']) for v in variations.values()), 'stale inspected coverage')
    require(not list(root.rglob('*.jpg')) and not list(root.rglob('*.gif')) and not list(root.rglob('*.mp4')), 'unexpected copied media')
    manifest_path = root / 'data/local-media.json'
    if manifest_path.exists():
        records = json.loads(manifest_path.read_text(encoding='utf-8'))
        require(len({r['reference_id'] for r in records}) == len(records), 'duplicate local media reference')
        for row in records:
            rid = row['reference_id']
            require(rid in refs, f'{rid}: orphan local media record')
            if rid in refs:
                require(row['source_url'] == refs[rid]['source_url'] and row['media_url'] == refs[rid]['media_url'], f'{rid}: local source mismatch')
                require(refs[rid].get('local_media_status') == row['status'], f'{rid}: stale local media status')
                for ref_field, manifest_field in [('local_path', 'local_path'), ('preview_path', 'preview_path'), ('local_sha256', 'sha256')]:
                    require(refs[rid].get(ref_field) == row.get(manifest_field), f'{rid}: local manifest mismatch for {ref_field}')
            if row['status'] != 'cached':
                require(not row.get('local_path'), f'{rid}: unavailable media has a local path')
                continue
            for field, sha_field in [('local_path', 'sha256'), ('preview_path', 'preview_sha256')]:
                if field == 'preview_path' and not row.get(field):
                    continue
                target = (root.parent / row.get(field, '')).resolve()
                require(target.is_relative_to((root.parent / 'work/reference-media').resolve()), f'{rid}: cache path escapes cache root')
                require(bool(re.fullmatch('[0-9a-f]{64}', row.get(sha_field, ''))), f'{rid}: missing cache hash')
                if local_media:
                    require(target.is_file(), f'{rid}: cached file missing')
                    if target.is_file() and target.is_relative_to((root.parent / 'work/reference-media').resolve()):
                        require(hashlib.sha256(target.read_bytes()).hexdigest() == row[sha_field], f'{rid}: cached file hash mismatch')
    elif local_media:
        require(False, 'local media manifest missing')
    return errors


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-media', action='store_true', help='Require cached files and verify SHA-256 hashes')
    failures = validate(local_media=parser.parse_args().local_media)
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: JSON, required fields, unique IDs, relationships, source correspondence, local links, coverage and media exclusions. Remote visual correspondence requires human/recorded inspection.')
