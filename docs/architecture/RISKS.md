# Risks and evidence gates

These are the active engineering/product risks, not unverified production incidents. Reconcile measurements with [the source report](../HEATSY_DEFORMATION_REPAIR.md) when a new build is available.

| Priority | Risk | Known evidence | Mitigation / decision |
| --- | --- | --- | --- |
| P0 | Muscle attachment and volume distortion | Bottom maximum ordinary-edge stretch 33.289→3.529×, but compression below 0.5× rises 1,292→3,139; 79.524 mm remaining upper-arm length change | [FMS-01](../plans/NEXT-SLICE.md): attachment-aware, region-by-region corrections; no indiscriminate smoothing |
| P1 | Native Blender parity | 10.0187 µm versus fixed 10 µm tolerance; underlying rest/pose reconstruction source not proven | Independently isolate precision path; keep strict gate, avoid hiding failed builds |
| P1 | Synthetic source technique | No independently captured pelvic tilt, twist or exercise review | Obtain rights-cleared movement and named reviewer before approval |
| P1 | Asset provenance / license | Heatsy model uses CC BY-SA 4.0; other motion sources have distinct rights | Retain source hashes/notices; publication gates must be independent of technical success |
| P2 | Preview performance | Software SwiftShader intervals much slower than Intel D3D11 in headless testing | Benchmark actual consumer hardware before optimization; no premature decimation |
| P2 | Editor outgrows renderer | Authoring experience could be built before animation works | Keep nontechnical editor deferred until quality proof |

**Release gate:** No asset marked approved or publicly ready until the relevant technical tests, license/provenance checks, movement review and anatomical review are independently recorded. [WORK](../knowledge/WORK.md) owns who works on each issue.
