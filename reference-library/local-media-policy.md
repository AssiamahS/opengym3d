# Local reference media policy and use

User-requested update, 2026-11-23: retain original reference media locally so another Codex can open it quickly. This supersedes the earlier external-links-only workflow. The library remains internal research, not a collection licensed for redistribution or production use.

## Files and retrieval

- [Local index](LOCAL-MEDIA.md) maps exercises/reference IDs to originals and PNG frame previews.
- [Manifest](data/local-media.json) retains source/attribution, original media URL, resolved download URL, status, byte count, SHA-256 and download timestamp.
- Paths are repository-relative, under ignored `work/reference-media/assets/` and `work/reference-media/previews/`. The cache also contains an offline INDEX.md and manifest.json.
- Reference JSON and CSV include `local_path`, `preview_path`, `local_sha256` and `local_media_status`. Follow a variation's reference IDs to those fields. Use previews for fast image inspection and originals for motion review.
- Animated-image previews use up to six evenly spaced frame indices. They are mechanical samples, not identified phases, a continuous review or human approval. Sources and inspection flags remain separate.
- Content hashes deduplicate identical downloads. Downloads are bounded to 80 MiB each; only recognized image/PDF/MP4 signatures are accepted. Previously cached files are hash-checked before reuse. Existing source evidence is not replaced.

Run `python reference-library/tools/cache_media.py`, then `python reference-library/tools/build.py`. Pillow is optional for downloads but needed for PNG previews (already available in this workspace). Run `python reference-library/tools/validate.py --local-media` to verify all declared local files and hashes. Default validation tolerates absent ignored caches on a fresh checkout; strict local validation does not.

## Source handling

The user authorized private local reference copies. This does not grant third-party redistribution rights. Keep originals, attribution and preview derivatives out of Git, public bundles and the application.

[StrengthLog's directory](https://www.strengthlog.com/exercise-directory/) states a conditional noncommercial, source-linking reuse allowance. We retain attribution and do not infer a commercial licence. Its image CDN returned 404 during this run; original public URLs embedded in those CDN paths worked. The manifest records the resolved publisher URL. The fallback is limited to this publisher and 404 responses; it does not bypass access denial.

[NHS terms section 3.5](https://www.nhs.uk/our-policies/terms-and-conditions/) exclude identifiable-person imagery from the general reuse grant. These images remain `source_restriction` pending permission. Hosted YouTube/Vimeo player URLs remain `external_player`; no video-stream extraction is attempted. Airedale direct videos failed certificate validation; TLS verification was not disabled. Other unavailable records explicitly distinguish absent direct media from retrieval failure.

All other cached assets retain their owners' rights, source citations and unknown redistribution status. Local availability is separate from visual correspondence, technical accuracy and public-use approval. A private handoff archive is for the same internal reference workflow, not a public asset release.
