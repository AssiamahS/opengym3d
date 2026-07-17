// Front/back anatomy bodymaps — the MuscleWiki signature: every exercise
// shows which muscles it hits on a body diagram, not just as text chips.
// Schematic (not a render): regions are simple paths, so this costs no CI
// time and no download. Colours match the 3D highlight — red = primary,
// orange = secondary, grey = rested.

const REGIONS = {
  front: {
    chest:      'M84,86 h32 a14,14 0 0 1 -16,20 a14,14 0 0 1 -16,-20 z M116,86 h32 a14,14 0 0 1 -16,20 a14,14 0 0 1 -16,-20 z',
    abs:        'M100,110 h32 v46 a16,16 0 0 1 -32,0 z',
    quads:      'M96,168 h30 v56 a15,15 0 0 1 -30,0 z M132,168 h30 v56 a15,15 0 0 1 -30,0 z',
    biceps:     'M70,92 h16 v40 a8,8 0 0 1 -16,0 z M172,92 h16 v40 a8,8 0 0 1 -16,0 z',
    forearms:   'M68,134 h16 v40 a8,8 0 0 1 -16,0 z M174,134 h16 v40 a8,8 0 0 1 -16,0 z',
    shoulders:  'M68,74 a18,14 0 0 1 22,-6 v18 h-22 z M190,74 a18,14 0 0 0 -22,-6 v18 h22 z',
    calves:     'M100,236 h22 v40 a11,11 0 0 1 -22,0 z M136,236 h22 v40 a11,11 0 0 1 -22,0 z',
    traps:      'M96,62 h66 v14 h-66 z',
  },
  back: {
    traps:      'M96,62 h66 v34 h-66 z',
    lats:       'M84,98 h90 v46 l-45,14 l-45,-14 z',
    'lower back':'M104,150 h50 v30 h-50 z',
    glutes:     'M96,182 h30 v34 a15,15 0 0 1 -30,0 z M132,182 h30 v34 a15,15 0 0 1 -30,0 z',
    hamstrings: 'M98,220 h28 v52 a14,14 0 0 1 -28,0 z M132,220 h28 v52 a14,14 0 0 1 -28,0 z',
    calves:     'M100,280 h22 v40 a11,11 0 0 1 -22,0 z M136,280 h22 v40 a11,11 0 0 1 -22,0 z',
    triceps:    'M70,92 h16 v42 a8,8 0 0 1 -16,0 z M172,92 h16 v42 a8,8 0 0 1 -16,0 z',
    shoulders:  'M68,74 a18,14 0 0 1 22,-6 v18 h-22 z M190,74 a18,14 0 0 0 -22,-6 v18 h22 z',
    forearms:   'M68,136 h16 v40 a8,8 0 0 1 -16,0 z M174,136 h16 v40 a8,8 0 0 1 -16,0 z',
  },
};

// Metadata muscle names -> region keys (same vocabulary the painter uses).
const ALIASES = {
  abs: 'abs', core: 'abs', chest: 'chest', pecs: 'chest',
  quads: 'quads', hamstrings: 'hamstrings', glutes: 'glutes',
  calves: 'calves', biceps: 'biceps', triceps: 'triceps',
  forearms: 'forearms', shoulders: 'shoulders', delts: 'shoulders',
  'front delts': 'shoulders', traps: 'traps', lats: 'lats', back: 'lats',
  'lower back': 'lower back',
};

const SILHOUETTE = `
  <circle cx="129" cy="40" r="20"/>
  <path d="M96,62 h66 v96 h-66 z"/>
  <path d="M96,158 h66 v26 h-66 z"/>
  <path d="M68,68 h28 v112 h-28 z"/>
  <path d="M162,68 h28 v112 h-28 z"/>
  <path d="M96,184 h30 v138 h-30 z"/>
  <path d="M132,184 h30 v138 h-30 z"/>
`;

function heatFor(ex) {
  const heat = {};
  for (const m of ex.secondary || []) {
    const k = ALIASES[m.toLowerCase()];
    if (k) heat[k] = 'secondary';
  }
  for (const m of ex.primary || []) {
    const k = ALIASES[m.toLowerCase()];
    if (k) heat[k] = 'primary';       // primary wins any overlap
  }
  return heat;
}

function panel(view, heat) {
  const paths = Object.entries(REGIONS[view]).map(([name, d]) => {
    const level = heat[name];
    return `<path class="rg ${level || 'rest'}" d="${d}"><title>${name}</title></path>`;
  }).join('');
  return `
    <figure class="bodymap">
      <svg viewBox="0 0 258 340" role="img" aria-label="${view} muscle map">
        <g class="silhouette">${SILHOUETTE}</g>
        ${paths}
      </svg>
      <figcaption>${view}</figcaption>
    </figure>`;
}

export function renderBodymap(el, ex) {
  const heat = heatFor(ex);
  el.innerHTML = panel('front', heat) + panel('back', heat);
}
