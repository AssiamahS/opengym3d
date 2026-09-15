// Rig inspector: the exported GLB carries every MakeHuman bone as a node plus
// the baked clip, so the skeleton can be drawn, scrubbed and graded right
// here — the same bones and the same numbers pipeline/qa_glb.py gates on.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const FPS = 30;
const JOINTS = {           // node -> label
  'upperarm01.L': 'L shoulder', 'lowerarm01.L': 'L elbow', 'wrist.L': 'L wrist',
  'upperarm01.R': 'R shoulder', 'lowerarm01.R': 'R elbow', 'wrist.R': 'R wrist',
  'upperleg01.L': 'L hip', 'lowerleg01.L': 'L knee', 'foot.L': 'L ankle',
  'upperleg01.R': 'R hip', 'lowerleg01.R': 'R knee', 'foot.R': 'R ankle',
  'root': 'pelvis', 'spine01': 'chest', 'neck01': 'neck', 'head': 'head',
};
const CHAIN_JOINTS = ['upperarm02.L', 'lowerarm02.L', 'upperarm02.R', 'lowerarm02.R',
  'upperleg02.L', 'lowerleg02.L', 'upperleg02.R', 'lowerleg02.R', 'spine03'];
const HINGE_NODE = { 'elbow.L': 'lowerarm01.L', 'elbow.R': 'lowerarm01.R',
  'knee.L': 'lowerleg01.L', 'knee.R': 'lowerleg01.R' };
const VIEWS = {              // glTF is Y-up; the figure faces +Z
  front: [0, 0.15, 1], side: [1, 0.15, 0.45], 'three-quarter': [0.7, 0.25, 0.7],
  back: [0, 0.15, -1], top: [0.001, 1, 0.001],
};

const $ = id => document.getElementById(id);
// GLTFLoader strips "." from node names (wrist.L -> wristL); look up both
const find = name => model && (model.getObjectByName(name) || model.getObjectByName(name.replace(/\./g, '')));
const stage = $('stage');
let renderer, labelRenderer, scene, camera, controls, stripRenderer;
let mixer, actions = [], clip, model, skeleton, box;
let joints = {}, labels = {}, contacts = [], propNodes = [], jointStatus = {};
let playing = true, meshVisible = true, xray = false;
const clock = new THREE.Clock();
let qa = null, entry = null;

function init() {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  stage.appendChild(renderer.domElement);
  labelRenderer = new CSS2DRenderer({ element: $('labels') });
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d10);
  scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x30343a, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(3, 5, 2);
  scene.add(sun);
  scene.add(new THREE.GridHelper(6, 24, 0x2a323c, 0x1a2027));
  camera = new THREE.PerspectiveCamera(40, 1, 0.05, 50);
  camera.position.set(1.8, 1.5, 2.6);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.9, 0);
  controls.enableDamping = true;
  stripRenderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  stripRenderer.setSize(220, 220);
  window.addEventListener('resize', resize);
  resize();
  renderer.setAnimationLoop(tick);
}

function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h);
  labelRenderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function time() { return actions[0] ? actions[0].time : 0; }
function setTime(t) {
  if (!clip) return;
  t = ((t % clip.duration) + clip.duration) % clip.duration;
  for (const a of actions) a.time = t;
  mixer.update(0);
  playing = false;
  $('play').textContent = '▶';
}

function tick() {
  if (mixer && playing) mixer.update(clock.getDelta());
  else clock.getDelta();
  if (clip) {
    const t = time();
    $('scrub').value = Math.round((t / clip.duration) * 1000);
    $('frame').textContent = `frame ${Math.round(t * FPS) + 1} / ${Math.round(clip.duration * FPS) + 1}  ${t.toFixed(2)}s`;
  }
  updateOverlays();
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();
function updateOverlays() {
  if (!model) return;
  for (const [name, sphere] of Object.entries(joints)) {
    const bone = find(name);
    if (bone) bone.getWorldPosition(sphere.position);
  }
  const lines = [];
  for (const c of contacts) {
    const w = find(c.wrist), p = find(c.prop);
    if (!w || !p) continue;
    w.getWorldPosition(tmp); p.getWorldPosition(tmp2);
    const d = tmp.distanceTo(tmp2);
    c.line.geometry.setFromPoints([tmp.clone(), tmp2.clone()]);
    c.line.material.color.set(d < 0.14 ? 0x3ecf7a : 0xff4d52);
    lines.push(`${c.wrist} → ${c.prop}: <b>${(d * 100).toFixed(1)} cm</b>`);
  }
  const angle = (a, b, c) => {
    const A = find(a), B = find(b), C = find(c);
    if (!A || !B || !C) return null;
    const pa = new THREE.Vector3(), pb = new THREE.Vector3(), pc = new THREE.Vector3();
    A.getWorldPosition(pa); B.getWorldPosition(pb); C.getWorldPosition(pc);
    return THREE.MathUtils.radToDeg(pa.sub(pb).angleTo(pc.sub(pb)));
  };
  const hinges = [
    ['L elbow', 'upperarm02.L', 'lowerarm01.L', 'lowerarm02.L'],
    ['R elbow', 'upperarm02.R', 'lowerarm01.R', 'lowerarm02.R'],
    ['L knee', 'upperleg02.L', 'lowerleg01.L', 'lowerleg02.L'],
    ['R knee', 'upperleg02.R', 'lowerleg01.R', 'lowerleg02.R'],
  ].map(([n, a, b, c]) => { const v = angle(a, b, c); return v == null ? '' : `${n} <b>${v.toFixed(0)}°</b>`; });
  $('readout').innerHTML = [...hinges, ...lines].join('<br>');
}

function clearModel() {
  if (model) scene.remove(model);
  if (skeleton) scene.remove(skeleton);
  for (const s of Object.values(joints)) scene.remove(s);
  for (const c of contacts) scene.remove(c.line);
  for (const l of Object.values(labels)) l.element.remove();
  joints = {}; labels = {}; contacts = []; propNodes = []; actions = [];
  model = skeleton = mixer = clip = null;
}

function statusOf(node) {
  return jointStatus[node] || 'PASS';
}

function buildJointStatus() {
  jointStatus = {};
  if (!qa) return;
  const worse = (a, b) => (a === 'FAIL' || b === 'FAIL') ? 'FAIL' : (a === 'warn' || b === 'warn') ? 'warn' : 'PASS';
  for (const r of qa.results) {
    if (r.status !== 'FAIL') continue;
    const level = r.critical ? 'FAIL' : 'warn';
    const nodes = r.joint.split('->').map(j => HINGE_NODE[j] || j);
    for (const n of nodes) jointStatus[n] = worse(jointStatus[n] || 'PASS', level);
  }
}

async function load(ex) {
  entry = ex;
  clearModel();
  $('qa').innerHTML = '<p class="muted">loading…</p>';
  $('verdict').className = 'badge NONE'; $('verdict').textContent = '…';
  $('ci-strip').innerHTML = '<p class="muted">—</p>';
  $('ci-sheet').innerHTML = '<p class="muted">—</p>';
  $('live-strip').innerHTML = '';

  qa = null;
  try {
    const r = await fetch(`assets/${ex.id}.glb.qa.json`, { cache: 'no-store' });
    if (r.ok) qa = await r.json();
  } catch (e) { /* no report on older deploys */ }
  buildJointStatus();
  renderQa();

  const gltf = await new GLTFLoader().loadAsync(`assets/${ex.id}.glb`);
  model = gltf.scene;
  scene.add(model);
  box = new THREE.Box3().setFromObject(model);
  model.traverse(o => {
    if (o.isMesh) {
      o.userData.mat = o.material;
      o.material = o.material.clone();
      o.material.transparent = true;
      o.material.depthWrite = true;
    }
  });
  applyMeshMode();

  mixer = new THREE.AnimationMixer(model);
  clip = gltf.animations.reduce((a, b) => (b.duration > a.duration ? b : a), gltf.animations[0]);
  for (const c of gltf.animations) {
    const a = mixer.clipAction(c);
    a.setLoop(THREE.LoopRepeat).play();
    actions.push(a);
  }
  const first = actions.find(a => a.getClip() === clip);
  actions = [first, ...actions.filter(a => a !== first)];

  const rig = model.getObjectByName('Human.rig') || model;
  skeleton = new THREE.SkeletonHelper(rig);
  skeleton.material.linewidth = 2;
  skeleton.visible = $('t-skel').classList.contains('on');
  scene.add(skeleton);

  for (const name of [...Object.keys(JOINTS), ...CHAIN_JOINTS]) {
    if (!find(name)) continue;
    const st = statusOf(name);
    const big = name in JOINTS;
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(big ? 0.02 : 0.012, 12, 12),
      new THREE.MeshBasicMaterial({ color: st === 'FAIL' ? 0xff4d52 : st === 'warn' ? 0xf2a51b : 0x3ecf7a, depthTest: false }));
    sphere.renderOrder = 10;
    sphere.visible = $('t-joints').classList.contains('on');
    scene.add(sphere);
    joints[name] = sphere;
    if (big) {
      const div = document.createElement('div');
      div.className = 'lbl ' + (st === 'PASS' ? '' : st);
      div.textContent = JOINTS[name];
      const lbl = new CSS2DObject(div);
      lbl.position.set(0, 0.03, 0);
      lbl.visible = $('t-labels').classList.contains('on');
      sphere.add(lbl);
      labels[name] = lbl;
    }
  }

  model.traverse(o => {
    if (o.isMesh && /^(barbell|dumbbell|kettlebell)/i.test(o.name)) propNodes.push(o.name);
  });
  for (const p of propNodes) {
    const sides = /\.(L|R)$/.exec(p);
    const wrists = sides ? ['wrist.' + sides[1]] : ['wrist.L', 'wrist.R'];
    for (const w of wrists) {
      const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x3ecf7a, depthTest: false }));
      line.renderOrder = 11;
      line.visible = $('t-contact').classList.contains('on');
      scene.add(line);
      contacts.push({ wrist: w, prop: p, line });
    }
  }

  playing = true; $('play').textContent = '⏸';
  setView(ex.camera === 'side' ? 'side' : 'three-quarter');
  mixer.update(0);
  facts();
  const img = new Image();
  img.onload = () => { $('ci-strip').innerHTML = ''; $('ci-strip').appendChild(img); };
  img.src = `assets/${ex.id}.strip.png`;
  const sheet = new Image();
  sheet.onload = () => { $('ci-sheet').innerHTML = ''; $('ci-sheet').appendChild(sheet); };
  sheet.src = ex.sheet || `assets/${ex.id}.sheet.png`;
  setTimeout(shootStrip, 300);
}

function facts() {
  const bits = [entry.equipment || 'None', entry.motion || '', `camera ${entry.camera || 'front'}`];
  if (propNodes.length) bits.push(`props: ${propNodes.join(', ')}`);
  if (clip) bits.push(`${(clip.duration).toFixed(2)}s, ${Math.round(clip.duration * FPS) + 1} frames`);
  $('facts').textContent = bits.join(' · ');
}

function renderQa() {
  const el = $('qa');
  if (!qa) {
    $('verdict').className = 'badge MISSING'; $('verdict').textContent = 'NO REPORT';
    el.innerHTML = '<p class="muted">No QA report for this GLB yet — it was rendered before the gate existed. Push to main to grade it.</p>';
    return;
  }
  const s = qa.summary;
  $('verdict').className = 'badge ' + (s.pass ? 'PASS' : 'FAIL');
  $('verdict').textContent = s.pass ? `PASS · ${s.fails} warning${s.fails === 1 ? '' : 's'}` : `FAIL · ${s.critical_fails} critical`;
  const groups = {};
  for (const r of qa.results) (groups[r.check] ||= []).push(r);
  const order = ['prop_present', 'prop_contact', 'bone_length', 'hinge', 'twist_flip', 'twist', 'spike', 'foot_slide', 'loop', 'skeleton'];
  let html = '';
  for (const check of order.filter(c => groups[c])) {
    const rows = groups[check];
    const bad = rows.filter(r => r.status === 'FAIL');
    html += `<h2>${check.replace('_', ' ')} <span class="muted">${rows.length - bad.length}/${rows.length} pass</span></h2><table>`;
    const shown = bad.length ? bad : rows.slice(0, 4);
    for (const r of shown) {
      const cls = r.status === 'FAIL' ? (r.critical ? 'FAIL' : 'warn') : 'PASS';
      const seek = r.t != null && r.status === 'FAIL';
      html += `<tr class="${cls}${seek ? ' seek' : ''}" data-t="${r.t ?? ''}"><td class="st">${cls === 'warn' ? 'WARN' : r.status}</td><td class="j">${r.joint}</td><td class="d">${r.detail}</td></tr>`;
    }
    if (!bad.length && rows.length > 4) html += `<tr><td></td><td colspan="2" class="d">… ${rows.length - 4} more, all pass</td></tr>`;
    html += '</table>';
  }
  el.innerHTML = html;
  el.querySelectorAll('tr.seek').forEach(tr => tr.onclick = () => setTime(Number(tr.dataset.t)));
}

function setView(name) {
  if (!box) return;
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  const dir = new THREE.Vector3(...VIEWS[name]).normalize();
  const dist = radius / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.05;
  camera.position.copy(center).addScaledVector(dir, dist);
  controls.target.copy(center);
  controls.update();
  document.querySelectorAll('#hud [data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === name));
}

function applyMeshMode() {
  if (!model) return;
  model.traverse(o => {
    if (!o.isMesh) return;
    o.visible = meshVisible;
    o.material.opacity = xray ? 0.28 : 1.0;
    o.material.depthWrite = !xray;
  });
}

function shootStrip() {
  if (!clip) return;
  const N = 12;
  const wasPlaying = playing, t0 = time();
  const cam = camera.clone();
  cam.aspect = 1; cam.updateProjectionMatrix();
  const wrap = $('live-strip');
  wrap.innerHTML = '';
  for (let i = 0; i < N; i++) {
    const t = (i / (N - 1)) * clip.duration * 0.999;
    setTime(t);
    updateOverlays();
    stripRenderer.render(scene, cam);
    const cell = document.createElement('div');
    cell.className = 'cell';
    const c = document.createElement('canvas');
    c.width = 220; c.height = 220;
    c.getContext('2d').drawImage(stripRenderer.domElement, 0, 0);
    c.onclick = () => setTime(t);
    const tag = document.createElement('span');
    tag.textContent = `f${Math.round(t * FPS) + 1}`;
    cell.append(c, tag);
    wrap.appendChild(cell);
  }
  setTime(t0);
  playing = wasPlaying;
  $('play').textContent = playing ? '⏸' : '▶';
}

// ---------------------------------------------------------------- UI wiring
$('play').onclick = () => { playing = !playing; $('play').textContent = playing ? '⏸' : '▶'; };
$('step-back').onclick = () => setTime(time() - 1 / FPS);
$('step-fwd').onclick = () => setTime(time() + 1 / FPS);
$('scrub').oninput = () => clip && setTime((Number($('scrub').value) / 1000) * clip.duration);
document.querySelectorAll('#hud [data-view]').forEach(b => b.onclick = () => setView(b.dataset.view));
const toggle = (id, fn) => { $(id).onclick = () => { $(id).classList.toggle('on'); fn($(id).classList.contains('on')); }; };
toggle('t-mesh', on => { meshVisible = on; applyMeshMode(); });
toggle('t-xray', on => { xray = on; applyMeshMode(); });
toggle('t-skel', on => skeleton && (skeleton.visible = on));
toggle('t-joints', on => Object.values(joints).forEach(s => s.visible = on));
toggle('t-labels', on => Object.values(labels).forEach(l => l.visible = on));
toggle('t-contact', on => contacts.forEach(c => c.line.visible = on));
$('restrip').onclick = shootStrip;
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'SELECT') return;
  if (e.key === ' ') { e.preventDefault(); $('play').click(); }
  if (e.key === 'ArrowLeft') $('step-back').click();
  if (e.key === 'ArrowRight') $('step-fwd').click();
});

async function main() {
  init();
  const manifest = await (await fetch('exercises.json')).json();
  let report = [];
  try { const r = await fetch('qa_report.json', { cache: 'no-store' }); if (r.ok) report = await r.json(); } catch (e) { /* older deploy */ }
  // the manifest is gated: failing exercises are missing from it on purpose,
  // but this page exists to look at exactly those — merge the QA report in
  const byId = Object.fromEntries(manifest.map(e => [e.id, e]));
  for (const r of report) if (!byId[r.id]) byId[r.id] = { id: r.id, name: r.id + ' (excluded)', equipment: '', motion: '', camera: 'front' };
  const list = Object.values(byId).sort((a, b) => a.id.localeCompare(b.id));
  const sel = $('exercise');
  for (const ex of list) {
    const rep = report.find(r => r.id === ex.id);
    const opt = document.createElement('option');
    opt.value = ex.id;
    opt.textContent = `${rep ? (rep.verdict === 'PASS' ? '✓' : '✕') : '·'} ${ex.name}`;
    sel.appendChild(opt);
  }
  sel.onchange = () => { location.hash = sel.value; };
  window.addEventListener('hashchange', () => {
    const id = location.hash.slice(1);
    if (byId[id]) { sel.value = id; load(byId[id]); }
  });
  const want = location.hash.slice(1);
  sel.value = byId[want] ? want : list[0].id;
  load(byId[sel.value]);
}
main();
