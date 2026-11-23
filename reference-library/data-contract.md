# Data contract — fms-reference/1

JSON arrays under `data/` are the normalized catalog; batch files retain curated research inputs. `tools/build.py` regenerates catalogs, CSV and review pages. Edit input batches, not generated entries. The family and equipment vocabulary inputs are explicitly provisional. Neither IDs nor name similarity confer approval.

Executed checks and limits are recorded in [VALIDATION](VALIDATION.md).

| Entity | Key relationships | Meaning |
| --- | --- | --- |
| Family | `variation_ids` | Editorial grouping by movement concept, not equipment or workout |
| Variation | `family`, `grip_id`, `equipment`, `equipment_configuration_ids`, `reference_ids` | Specific technique and contacts; all currently partial/unreviewed |
| Equipment | independent ID | Generic vocabulary item or exact manufacturer model; dimensions may be null |
| Configuration | `variation_id`, `equipment_id` | Particular setup and contact interpretation; unknown adjustments stay null |
| Equipment alternative group | `variation_ids`, selection context and differences | Explicit candidate variations for a workout slot; each member retains its own equipment, grip and configuration |
| Grip | `variation_ids`, `reference_ids`, optional `supporting_variation_reference_ids` | Hand/implement relationship; contact labels are not anatomical presets |
| Reference | `owner_type`, `owner_id`, `source_id` | Single source/media evidence record with access date, view, phase and verification depth |
| Source | URL and organization | Original external publication; rights retained |
| Phase | variation-local ID | Description plus evidence basis; not a trajectory or keyframe |
| Workout | intentionally absent | Future composition of variation IDs, repetitions, durations and rest |

`source_urls` can include unresolved research leads; read the associated `verification` and `missing_evidence`, not just the URL. `reference_ids` may identify text-only product pages rather than imagery. Filter by non-null `media_url` and then by `visual_inspected` when seeking inspected imagery. A true inspection flag can represent only one visible GIF frame. It does not mean the complete movement or grip was verified.

Some original batch `movement.end` fields describe the extreme posture and others describe the finished repetition. The phase table marks this limitation instead of silently converting an end posture to a bottom pose. Do not consume that field as a keyframe contract. Use explicit curated phases where present; null phases require further research.

`guidance` is source paraphrase; `movement.basis` identifies qualitative interpretation. Technical measurements are absent. `confidence` is descriptive and intentionally not a calibrated numerical score. No `complete` or human-approved variation is emitted in this version.

CSV list cells use JSON arrays. IDs remain stable across source-page moves. Reference/source hashes identify provenance records, not exercise identity. The validator checks duplicate IDs, required fields, foreign keys, source/owner correspondence, local Markdown links and count consistency. It does not test future remote URL availability, anatomical correctness or redistribution rights.

Batch 02 references can contain `observed_samples` with locator, view, phase, observation and limitations. A video locator is a sampled player time; a GIF snapshot is explicitly untimed; a PDF locator identifies the page and panel. `full_cycle_reviewed: false` distinguishes those samples from continuous motion review. Explicit boolean visual flags require recognized inspection attestations. `excluded_references` preserves rejected media matches without including them as positive evidence.

`equipment_alternative_group_ids` links a variation back to [equipment choices](EQUIPMENT-ALTERNATIVES.md). Groups are curated in `data/equipment-alternative-groups.json`; their members must exist and cannot be `research_required`. Membership is a selection aid, not biomechanical equivalence, a prescription, or permission to reuse one animation with another implement.

References may carry `temporal_alignment` to explain how a sample's displayed frame was associated with its media time, and `revalidation_note` to preserve a later unsuccessful replay. These descriptive fields do not override `verification`, `visual_inspected` or `full_cycle_reviewed`. Millisecond media offsets are locators, not motion-event measurements.

`aliases` is an optional input list of common search names, normalized to an empty list when absent and exported in variation JSON, CSV and pages. Aliases never create new families.

Local-reference update: use [local media and previews](LOCAL-MEDIA.md) and [cache policy](local-media-policy.md). Original files stay in ignored `work/reference-media`; download status is independent of visual inspection.

Reference records now include `local_media_status`, `local_path`, `preview_path` and `local_sha256`. Paths are repository-relative; absent media uses null paths. `data/local-media.json` maps reference IDs to original/resolved URLs, byte counts, SHA-256, retrieval time, automatic frame indices and explicit failure reasons. Optional ignored-cache links are excluded from portable link requirements; `--local-media` makes existence and integrity mandatory.
