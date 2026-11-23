# Equipment inspection, use and guidance

This is a separate experimental MPFB proof authorized by the equipment-use
request. It does not approve the Heatsy deformation work or supersede its gates.

## Three independent levels

1. **Inspection:** a catalog entry describes equipment geometry, supported
   configuration, named contact frames and compatible variations. Its standalone
   GLB can be loaded and rotated without loading an anatomical character.
2. **Use demonstration:** a variation combines a movement source, character rig
   adapter, equipment asset and explicit attachment/kinematic recipe. The goblet
   recipe must alter arm/hand posture; equipment substitution alone is not a
   technique definition. Its baked GLB contains the synchronized character and
   implement for playback in ordinary consumers.
3. **Guidance:** camera presets, setup text, direction indicators and optional
   form notes are presentation metadata. They do not alter skeletal motion or
   claim clinical/instructional approval. A separate MP4 page loads no 3D code.

The first proof uses the existing synthetic squat and MPFB asset. The standalone
dumbbell and demonstrated dumbbell reuse the same procedural geometry. An
exercise change does not require designing new equipment geometry. Inspection
configuration is explicitly separate from the fixed configuration of a tested
demonstration; changing dimensions cannot silently invalidate its contacts.

## Initial reusable catalog

The continuation from `ad14fa7` adds dumbbell, kettlebell and barbell inspection
assets through `studio/equipment_catalog.py`. It calls the existing procedural
builders; it does not invoke the movement or character pipeline. A generator and
asset hash cache preserves static GLBs across exercise builds. Thumbnail renders,
dimensions in metres, glTF Y-up nominal contact positions, display configuration,
MIT license and source provenance live in `equipment-catalog/1` metadata.
`compatibleVariations` is explicit: only the dumbbell offers the experimental
goblet fixture. Neither a new implement nor inspection scaling creates a technique.

The gallery requests metadata and small WebP thumbnails first, with no GLB request
until selection. The existing Three.js viewer owns a bounded two-asset cache,
one active mixer and serialized loading. Superseded loads are disposed, old
mixers are stopped and uncached, and evicted geometry/materials/textures are
released. Returning to the gallery retains that bounded cache; leaving the page
cleans it up. Camera framing uses selected geometry bounds. Quick Peek remains a
separate video-only page with no 3D dependency.

All continuation writes are restricted by `equipment_paths.py` to
`outputs/equipment-library/`, including candidate subdirectories. The previous
`outputs/equipment-use/` proof and the original 1,139-file protected manifest are
preserved. Independent catalog validation checks exported dimensions, static
structure, hashes, nominal handle targets and license files. Browser checks cover
lazy loading, races, repeated transitions, resource counts and screenshot evidence.
Integration requires current catalog, asset and viewer hashes; a stale browser
report cannot restore a technical PASS.

Executed measurements, before/after images and remaining thumb limitations are
recorded in the [library milestone review](../EQUIPMENT_LIBRARY_REVIEW.md).

## Contracts and evidence

- Equipment owns dimensions, geometry, contact frames and configuration limits.
- Movement owns source motion and timing, not which implement is compatible.
- Variation owns pose/attachment constraints and compatible equipment setup.
- Rig adaptation owns character-specific joint and hand alignment.
- Guidance owns labels, views, setup and optional indicators.
- Validation owns exported-artifact contact/orientation/stability evidence,
  collision scope and provenance. A self-defined contact marker is insufficient
  evidence of visible surface contact on its own.

Technical, visual, movement and human-approval statuses stay separate. A
technically synchronized synthetic repetition is not approved exercise guidance.
Preserve all previous baselines, expose unresolved penetration or grip defects,
and retain source/asset license notices alongside generated artifacts.

## Future capabilities, not implemented by this proof

Cable machines need cable endpoints, pulley paths and synchronized travel.
Leg presses need foot-platform contacts and carriage constraints. Benches need
support/contact regions and clearance checks. Smith machines need constrained
bar travel and grip relationships. These require articulated equipment joints,
body-to-equipment constraints and variation-specific kinematics. They do not
justify a general machine physics engine in this milestone.

Future configuration changes must revalidate reach, grip and clearances. A
dumbbell goblet recipe must not be reused automatically for a barbell, cable,
machine or differently sized handle.
