"""Build review pages and normalized data from explicitly curated research inputs.

No network, media copying, technique generation, or animation integration.
Run from any directory with Python's standard library.
"""
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATE = '2026-11-23'


def is_visually_inspected(ref):
    """Use an explicit flag when supplied; retain exact legacy attestations."""
    inspected_statuses = {
        'visually_inspected', 'visually_inspected_single_frame', 'visually_inspected_sampled_frames',
        'Page text and source-discovered media URL checked; actual browser screenshot visually inspected 2026-11-23. Single frame only; no timing or full-cycle validation.'
    }
    if 'visual_inspected' in ref:
        if not isinstance(ref['visual_inspected'], bool):
            raise ValueError('visual_inspected must be a boolean')
        if ref['visual_inspected'] and ref['verification'] not in inspected_statuses:
            raise ValueError('Positive visual flag requires a recognized inspection attestation')
        return ref['visual_inspected']
    return ref['verification'] in inspected_statuses


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def write(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value.rstrip() + '\n' if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sid(prefix, value):
    return prefix + '.' + hashlib.sha256(value.encode()).hexdigest()[:12]


def label(value):
    return value.replace('-', ' ').capitalize()


def cell(value):
    if value is None:
        return 'Unknown'
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace('|', '\\|').replace('\n', ' ')


def table(rows):
    return '\n'.join('| ' + ' | '.join(map(cell, r)) + ' |' for r in rows) + '\n'


def csv_file(name, rows, fields):
    with (ROOT / 'data' / name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in fields})


def main():
    local_manifest = read('data/local-media.json') if (ROOT / 'data/local-media.json').exists() else []
    local_by_id = {r['reference_id']: r for r in local_manifest}
    variations = []
    for batch in ['freeweights', 'upperbody', 'machines', 'expansion-02', 'visual-expansion-02', 'breadth-05-lower', 'breadth-05-upper', 'breadth-05-core', 'breadth-05-mobility']:
        for record in read(f'batches/{batch}.json'):
            record['batch'] = batch
            variations.append(record)
    family_map = {
        'dumbbell-bulgarian-split-squat': 'split-squat', 'dumbbell-deadlift': 'deadlift',
        'dumbbell-romanian-deadlift': 'romanian-deadlift', 'kettlebell-single-leg-deadlift': 'deadlift',
        'kettlebell-swing-two-hand': 'kettlebell-swing', 'kettlebell-swing-one-hand': 'kettlebell-swing',
        'kettlebell-clean': 'clean', 'kettlebell-clean-press': 'clean-and-press',
        'kettlebell-double-press': 'overhead-press', 'kettlebell-push-press': 'push-press',
        'kettlebell-windmill': 'windmill', 'kettlebell-thruster-double': 'thruster',
        'kettlebell-thruster-single': 'thruster', 'side-plank': 'side-plank',
        'crunch': 'crunch', 'dead-bugs': 'dead-bug', 'hanging-knee-raise': 'knee-raise',
        'mountain-climbers': 'mountain-climber', 'chin-up': 'chin-up',
        'precor-rsl0515-shoulder-press': 'overhead-press'
    }
    grip_alias = {'none': 'no-hand-load', 'no-grip': 'no-hand-load',
                  'bar-pronated': 'pronated-closed', 'bar-supinated': 'supinated-closed',
                  'goblet-dumbbell-head': 'dumbbell-goblet-head-support'}
    inventory = read('data/family-inventory.json')
    alternative_groups = read('data/equipment-alternative-groups.json')
    families = {id_: {'id': id_, 'name': label(id_), 'category': cat, 'reference_status': 'research_required', 'variation_ids': [], 'source_urls': [], 'basis': 'Editorial inventory; direct technique research pending.'}
                for cat, ids in inventory.items() for id_ in ids}
    equipment = {e['id']: dict(e, name=label(e['id']), basis='Provisional equipment vocabulary; typical components are engineering hypotheses, not a verified model specification.', source_urls=[], reference_status='research_required', dimensions=None, review_status='unreviewed') for e in read('data/equipment-vocabulary.json')}
    grips = {grip_alias.get(g['id'], g['id']): dict(g) for g in read('batches/grips.json')}
    for id_, g in grips.items():
        g['id'] = id_
        g['review_status'] = 'unreviewed'
        g['reference_status'] = 'partial' if g['source_urls'] else 'research_required'
        g['variation_ids'] = []
        g.setdefault('basis', 'Source-specific grip guidance; closure and contact details may remain unknown.')
    references, sources, configurations = [], {}, []

    def add_ref(ref, owner, owner_type):
        ref = dict(ref)
        ref['id'] = sid('ref', owner_type + owner + ref['source_url'] + str(ref.get('media_url')))
        cached = local_by_id.get(ref['id'], {})
        ref['local_media_status'] = cached.get('status', 'not_attempted')
        ref['local_path'] = cached.get('local_path')
        ref['preview_path'] = cached.get('preview_path')
        ref['local_sha256'] = cached.get('sha256')
        ref['owner_id'], ref['owner_type'] = owner, owner_type
        ref.setdefault('access_date', DATE)
        ref['rights'] = 'External rights retained; redistribution permission not established.'
        ref['source_id'] = sid('source', ref['source_url'])
        ref['view'] = None if ref.get('view') in ('unknown', 'not visually inspected') else ref.get('view')
        ref['phase'] = None if ref.get('phase') in ('unknown', 'equipment setup and mechanism', 'grip setup') else ref.get('phase')
        ref['visual_inspected'] = is_visually_inspected(ref)
        ref.setdefault('full_cycle_reviewed', False)
        sources[ref['source_id']] = {'id': ref['source_id'], 'url': ref['source_url'], 'organization': ref.get('organization', urlsplit(ref['source_url']).hostname), 'access_date': DATE, 'verification': 'See individual reference verification; some sources are leads only.', 'rights': ref['rights']}
        references.append(ref)
        return ref['id']

    for v in variations:
        v['family'] = family_map.get(v['id'], v['family'])
        v['grip_id'] = grip_alias.get(v['grip_id'], v['grip_id'])
        if v['family'] not in families:
            families[v['family']] = {'id': v['family'], 'name': label(v['family']), 'category': v['category'], 'variation_ids': [], 'source_urls': []}
        f = families[v['family']]
        f['variation_ids'].append(v['id'])
        f['source_urls'] = sorted(set(f['source_urls'] + v['source_urls']))
        f['reference_status'] = 'partial'
        f['basis'] = 'Has source-indexed variations; family taxonomy is editorial.'
        v.setdefault('aliases', [])
        v['review_status'] = 'unreviewed'
        v.setdefault('reference_status', 'partial')
        v['schema_version'] = 'fms-reference/1'
        v['access_date'] = DATE
        v['movement'].setdefault('basis', 'Qualitative engineering inference from source instructions, not measured biomechanics.')
        v.setdefault('source_conflicts', [])
        if v['id'] == 'dumbbell-squat-sides':
            conflict = 'Source text permits side hold; its inspected GIF shows shoulder hold. Do not use that GIF as side-hold evidence.'
            if conflict not in v['source_conflicts']:
                v['source_conflicts'].append(conflict)
        if v['id'] == 'dumbbell-romanian-deadlift':
            conflict = 'NASM cues stopping short of full hip extension; StrengthLog returns to standing. Preserve source-specific endpoints for human review.'
            if conflict not in v['source_conflicts']:
                v['source_conflicts'].append(conflict)
        v.setdefault('conflict_review', 'Incomplete; absence of recorded conflicts is not consensus.')
        v['equipment_alternative_group_ids'] = [g['id'] for g in alternative_groups if v['id'] in g['variation_ids']]
        v['reference_ids'] = [add_ref(r, v['id'], 'variation') for r in v.pop('references')]
        v['equipment_configuration_ids'] = []
        for eid in v['equipment']:
            if eid not in equipment:
                machine = v.get('machine', {})
                equipment[eid] = {'id': eid, 'name': machine.get('model', label(eid)), 'components': None, 'contacts': machine.get('contacts'), 'adjustments': machine.get('adjustments'), 'moving_parts': machine.get('moving_components'), 'source_urls': v['source_urls'], 'basis': 'Manufacturer text plus explicitly marked motion inference; product geometry not measured.' if machine else 'Equipment identity from exercise source only; components and dimensions not researched.', 'reference_status': 'partial', 'dimensions': None, 'review_status': 'unreviewed'}
            cid = 'config.' + v['id'] + '.' + eid
            configurations.append({'id': cid, 'variation_id': v['id'], 'equipment_id': eid, 'setup': v['movement']['start'], 'hand_contacts': v['movement']['hands_contact'], 'foot_contacts': v['movement']['feet_contact'], 'body_support': v['movement']['torso'], 'equipment_motion': v['movement']['equipment_motion'], 'adjustment_values': None, 'machine': v.get('machine'), 'basis': v['movement']['basis'], 'review_status': 'unreviewed'})
            v['equipment_configuration_ids'].append(cid)
        gid = v['grip_id']
        if gid not in grips:
            grips[gid] = {'id': gid, 'name': label(gid), 'palm': None, 'thumb': None, 'fingers': None, 'wrist': None, 'contacts': None, 'source_urls': [], 'references': [], 'confidence': 'low; contact label only', 'missing_evidence': ['Close-up views', 'Finger and thumb contact', 'Human approval'], 'basis': 'Variation-derived contact category, not an anatomical preset.', 'reference_status': 'research_required', 'review_status': 'unreviewed', 'variation_ids': []}
        grips[gid]['variation_ids'].append(v['id'])
        grips[gid]['source_urls'] = sorted(set(grips[gid]['source_urls'] + v['source_urls']))
        v.setdefault('movement_phases', [
            {'id': 'setup', 'description': v['movement']['start'], 'basis': 'source-guided interpretation'},
            {'id': 'action', 'description': v['movement']['motions'], 'basis': v['movement']['basis']},
            {'id': 'endpoint', 'description': v['movement']['end'], 'basis': 'Batch field: may mean extreme position OR completed repetition; inspect source before using.'},
            {'id': 'return', 'description': None, 'basis': 'Separate return trajectory and timing not verified.'}
        ])
        for phase in v['movement_phases']:
            if 'phase' in phase:
                phase['id'] = phase.pop('phase')
    # Extend the requested grip vocabulary without pretending unsupported entries are researched.
    for gid in ['false-thumbless', 'cable-rope', 'd-handle', 'farmers-carry', 'plate-pinch', 'dumbbell-vertical-shaft']:
        if gid not in grips and not (gid == 'dumbbell-vertical-shaft' and 'vertical-dumbbell-shaft' in grips):
            grips[gid] = {'id': gid, 'name': label(gid), 'palm': None, 'thumb': None, 'fingers': None, 'wrist': None, 'contacts': None, 'source_urls': [], 'references': [], 'confidence': 'unknown', 'missing_evidence': ['Primary technique source', 'Multiple grip close-ups', 'Human approval'], 'basis': 'Requested inventory target only.', 'reference_status': 'research_required', 'review_status': 'unreviewed', 'variation_ids': []}
    # Carry direct observed evidence into matching grip records without claiming fine contact resolution.
    for gid, vid in [('kettlebell-horns', 'kettlebell-goblet-squat'), ('dumbbell-goblet-head-support', 'dumbbell-goblet-head-support')]:
        g = grips[gid]
        v = next(x for x in variations if x['id'] == vid)
        g['supporting_variation_reference_ids'] = v['reference_ids']
        g['reference_status'] = 'partial'
        g['missing_evidence'].append('Fine thumb and finger contact unresolved in whole-body images.')
    for g in grips.values():
        g['reference_ids'] = [add_ref(r, g['id'], 'grip') for r in g.pop('references', [])]
    datasets = {'exercise-families': list(families.values()), 'exercise-variations': variations, 'equipment': list(equipment.values()), 'equipment-configurations': configurations, 'equipment-alternative-groups': alternative_groups, 'grip-archetypes': list(grips.values()), 'references': references, 'sources': list(sources.values())}
    for name, records in datasets.items():
        write('data/' + name + '.json', records)
    csv_file('exercise-variations.csv', variations, ['id', 'family', 'name', 'aliases', 'equipment', 'grip_id', 'equipment_alternative_group_ids', 'reference_status', 'review_status', 'source_urls', 'reference_ids', 'missing_evidence'])
    csv_file('references.csv', references, ['id', 'owner_type', 'owner_id', 'source_url', 'media_url', 'type', 'view', 'phase', 'visual_inspected', 'verification', 'access_date', 'rights', 'local_media_status', 'local_path', 'preview_path', 'local_sha256'])
    csv_file('exercise-families.csv', list(families.values()), ['id', 'name', 'category', 'reference_status', 'variation_ids'])
    ref_by_id = {r['id']: r for r in references}
    for v in variations:
        body = f"# {v['name']}\n\nID: `{v['id']}` · **{v['reference_status'].upper()} / human unreviewed** · {DATE}\n\n[Library](../../INDEX.md) · [Family](INDEX.md)\n\n{v['guidance']}\n\n"
        body += f"Equipment: {', '.join('[%s](../../equipment/%s.md)' % (e,e) for e in v['equipment']) or 'Bodyweight / floor contacts'}\n\nGrip: [{v['grip_id']}](../../grips/{v['grip_id']}.md). Configuration IDs: {', '.join(v['equipment_configuration_ids']) or 'None'}.\n\n"
        if v['aliases']:
            body += 'Search aliases: ' + ', '.join(v['aliases']) + '\n\n'
        if v['equipment_alternative_group_ids']:
            body += 'Equipment choices for a workout slot: ' + ', '.join(f'[{gid}](../../EQUIPMENT-ALTERNATIVES.md#{gid})' for gid in v['equipment_alternative_group_ids']) + '. Select a separate variation; its grip and contacts remain specific.\n\n'
        body += '## Movement interpretation\n\n' + table([['Field', 'Description'], ['---', '---']] + list(v['movement'].items()))
        body += '\n## Phase map\n\n' + table([['Phase', 'Description', 'Basis'], ['---', '---', '---']] + [[p['id'], p['description'], p['basis']] for p in v['movement_phases']])
        body += '\n## Visual evidence\n\n'
        for rid in v['reference_ids']:
            r = ref_by_id[rid]
            if r.get('local_path'):
                body += f"- **Local original:** [Open](../../../{r['local_path']})"
                if r.get('preview_path'):
                    body += f" · [Frame preview](../../../{r['preview_path']})"
                body += ' (automatic samples are not verified phases).\n'
            body += f"- [{r['organization']} source]({r['source_url']})" + (f" · [Open media]({r['media_url']})" if r['media_url'] else ' · Matching media unavailable') + f" — {r['description']} Verification: {r['verification']}. View: {r['view'] or 'unknown'}; phase: {r['phase'] or 'unknown'}.\n"
            if r['visual_inspected'] and r['type'] in ['image', 'photo', 'gif', 'animated-gif', 'photo-collage']:
                body += f"\n![External {r['organization']} reference; only recorded frame inspected]({r['media_url']})\n\n"
            if r.get('observed_samples'):
                body += '\n' + table([['Sample', 'View', 'Phase', 'Observation / limit'], ['---'] * 4] + [[s['locator'], s['view'], s['phase'], s['observation'] + ' ' + s.get('limitations', '')] for s in r['observed_samples']]) + '\n'
        body += '\nLocal copies, where available, are internal references in the ignored cache. No redistribution grant established.\n\n## Missing evidence and conflicts\n\n' + '\n'.join('- ' + x for x in v['missing_evidence'] + v['source_conflicts']) + '\n\n' + v['conflict_review'] + '\n'
        if 'machine' in v:
            body += '\n## Model-specific machine contacts\n\n' + table([['Field', 'Evidence'], ['---', '---']] + list(v['machine'].items()))
        if v.get('excluded_references'):
            body += '\n## Excluded visual matches\n\n' + table([['Media', 'Reason'], ['---', '---']] + [[f"[Source media]({r['media_url']})", r['reason']] for r in v['excluded_references']])
        write(f"exercises/{v['family']}/{v['id']}.md", body)
    for f in families.values():
        if f['variation_ids']:
            write(f"exercises/{f['id']}/INDEX.md", '# ' + f['name'] + '\n\n' + '\n'.join(f'- [{id_}]({id_}.md)' for id_ in f['variation_ids']) + '\n')
    for e in equipment.values():
        write(f"equipment/{e['id']}.md", f"# {e['name']}\n\n[Library](../INDEX.md) · {e['reference_status']} / unreviewed\n\n" + table([['Field', 'Value'], ['---', '---']] + list(e.items())) + '\n' + '\n'.join(f'- [Source]({u})' for u in e['source_urls']) + '\n')
    for g in grips.values():
        write(f"grips/{g['id']}.md", f"# {g['name']}\n\n[Library](../INDEX.md) · {g['reference_status']} / unreviewed\n\n" + table([['Field', 'Value'], ['---', '---']] + [(k,v) for k,v in g.items() if k not in ['source_urls']]) + '\n' + '\n'.join(f'- [Source]({u})' for u in g['source_urls']) + '\n')
    write('VISUAL-INDEX.md', '# Searchable visual-reference index\n\nSearch this page by variation, grip, phase or source; use [CSV](data/references.csv) for filtering. Unknown angles are not inferred. Original source links open externally; see [local cache](LOCAL-MEDIA.md) for downloaded originals and previews.\n\n' + table([['Owner', 'Type', 'View / phase', 'Media', 'Source', 'Inspection'], ['---'] * 6] + [[r['owner_id'], r['type'], str(r['view']) + ' / ' + str(r['phase']), f"[Open]({r['media_url']})" if r['media_url'] else 'Missing', f"[Source]({r['source_url']})", r['verification']] for r in references]))
    counts = {k: len(v) for k,v in datasets.items()}
    counts['variations_with_visual_inspection'] = sum(any(ref_by_id[r]['visual_inspected'] for r in v['reference_ids']) for v in variations)
    counts['variations_with_multiple_references'] = sum(len(v['reference_ids']) >= 2 for v in variations)
    counts['complete_variations'] = 0
    counts['partial_variations'] = sum(v['reference_status'] == 'partial' for v in variations)
    counts['research_required_variations'] = sum(v['reference_status'] == 'research_required' for v in variations)
    counts['references_with_sample_locators'] = sum(bool(r.get('observed_samples')) for r in references)
    counts['full_cycle_reviewed_references'] = sum(r['full_cycle_reviewed'] for r in references)
    counts['human_approved'] = 0
    counts['families_with_variations'] = sum(bool(f['variation_ids']) for f in families.values())
    counts['references_with_local_media'] = sum(bool(r.get('local_path')) for r in references)
    counts['variations_with_local_media'] = sum(any(ref_by_id[r].get('local_path') for r in v['reference_ids']) for v in variations)
    counts['unique_local_media_files'] = len({r['local_path'] for r in references if r.get('local_path')})
    write('data/coverage.json', counts)
    write('LOCAL-MEDIA.md', '# Local media for Codex\n\nPaths below are relative to the repository root. Originals and automatic frame previews live in ignored `work/reference-media/`. Downloads do not change visual-inspection or human-approval status. Run `python reference-library/tools/cache_media.py`, then rebuild and run `python reference-library/tools/validate.py --local-media`. See [cache policy](local-media-policy.md).\n\n' + table([['Reference / exercise', 'Status', 'Local original', 'Preview', 'Source'], ['---'] * 5] + [[r['owner_id'] + ' / ' + r['id'], r['local_media_status'], f"[Open](../{r['local_path']})" if r.get('local_path') else 'Unavailable', f"[Preview](../{r['preview_path']})" if r.get('preview_path') else 'Unavailable', f"[Source]({r['source_url']})"] for r in references]))
    var_by_id = {v['id']: v for v in variations}
    alternatives_page = '# Equipment alternatives for workout selection\n\nThese groups keep sensible equipment choices discoverable. A workout chooses a member variation; each retains its own grip, contacts, configuration and evidence. They do not replace equipment inside an animation or assert equal loads.\n\n'
    for g in alternative_groups:
        alternatives_page += f"## {g['id']}\n\n{g['selection_context']}\n\n" + '\n'.join(f"- [{var_by_id[vid]['name']}](exercises/{var_by_id[vid]['family']}/{vid}.md)" for vid in g['variation_ids']) + '\n\n' + ' '.join(g['differences']) + '\n\nBasis: ' + g['basis'] + '\n\n'
    write('EQUIPMENT-ALTERNATIVES.md', alternatives_page)
    write('COVERAGE.md', '# Coverage and confidence\n\n**PARTIAL research collection, not a completed comprehensive library.** Checked ' + DATE + '.\n\n' + table([['Measure', 'Count'], ['---', '---']] + list(counts.items())) + '\nCurrent breadth-first target: approximately 300 distinct exercise families, usually 1–3 useful variations each. The original 1,000–2,000-variation depth target is deferred. Fine contact gaps do not block expansion. Inventory-only families do not count as researched. No batch meets complete multi-view, phase and close-up requirements yet. Single inspected frames do not establish full playback. Eight machine records concern one manufacturer only. Broad equipment vocabulary is not a dimensional asset catalog.\n\n[Continuation queue](research-gaps/continuation.md) · [Research method](research-method.md)\n\n' + table([['Family', 'Category', 'Researched variation count', 'Status'], ['---'] * 4] + [[f['id'], f['category'], len(f['variation_ids']), f['reference_status']] for f in families.values()]))
    write('research-gaps/missing-images.md', '# Missing visual evidence\n\nEach record still needs complementary views and detailed contact review. Exact deficits follow.\n\n' + '\n'.join(f"- [{v['name']}](../exercises/{v['family']}/{v['id']}.md): " + '; '.join(v['missing_evidence']) for v in variations) + '\n')
    write('research-gaps/unverified-variations.md', '# Inventory families awaiting direct variation research\n\nThese are discovery targets, not verified exercise recipes. Do not generate all combinations of equipment and grips.\n\n' + '\n'.join('- ' + f['id'] for f in families.values() if not f['variation_ids']) + '\n')
    write('equipment/MACHINE-CONTACTS.md', '# Machine contacts and motion\n\nModel-specific product text is only an initial constraint inventory. User demonstrations, placards, pivots, travel, cables and resistance linkage still require verification.\n\n' + table([['Model', 'Exercise', 'Adjustments', 'Supports', 'Moving components', 'Unresolved'], ['---'] * 6] + [[v['machine']['model'], f"[{v['name']}](../exercises/{v['family']}/{v['id']}.md)", v['machine']['adjustments'], v['machine']['supports'], v['machine']['moving_components'], v['missing_evidence']] for v in variations if 'machine' in v]))
    write('INDEX.md', '# Forged Motion Studio visual exercise reference library\n\nInternal research · ' + DATE + ' · **PARTIAL, human unreviewed**\n\n' + f"{len(variations)} source-indexed variations; {counts['variations_with_visual_inspection']} have limited inspected visual evidence. " + 'Current goal: broad coverage toward approximately 300 distinct families with usually 1–3 useful variations each; detailed variations follow on demand.\n\n- [Coverage and confidence](COVERAGE.md)\n- [Local media and previews](LOCAL-MEDIA.md)\n- [Visual-reference index](VISUAL-INDEX.md)\n- [Equipment alternatives](EQUIPMENT-ALTERNATIVES.md)\n- [Batch 05 breadth findings](batches/batch-05-review.md)\n- [Batch 04 findings](batches/batch-04-review.md)\n- [Batch 03 findings](batches/batch-03-review.md)\n- [Batch 02 findings](batches/batch-02-review.md)\n- [Research method](research-method.md)\n- [Codex integration guide](integration-guide.md)\n- [Machine contacts](equipment/MACHINE-CONTACTS.md)\n- [Continuation queue](research-gaps/continuation.md)\n- [Missing images](research-gaps/missing-images.md)\n- [Disputed techniques](research-gaps/disputed-techniques.md)\n- [Source survey](sources.md)\n- [Data contract](data-contract.md)\n\n## Data\n\n' + '\n'.join(f'- [{k}](data/{k}.json)' for k in datasets) + '\n\n[Variation CSV](data/exercise-variations.csv) · [Reference CSV](data/references.csv) · [Family CSV](data/exercise-families.csv)\n\n## Exercise pages\n\n' + '\n'.join(f"- [{f['name']}](exercises/{f['id']}/INDEX.md) ({len(f['variation_ids'])})" for f in families.values() if f['variation_ids']) + '\n\n## Rebuild and validate\n\nRun `python reference-library/tools/build.py`, then `python reference-library/tools/validate.py`. Inputs are the curated batch JSON plus family/equipment inventory. Generated pages and catalogs are Git-ready research text; downloaded third-party media stays in ignored work/reference-media and is excluded from public bundles.\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
