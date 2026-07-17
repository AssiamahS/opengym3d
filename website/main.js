import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { renderBodymap } from './bodymap.js';

const grid = document.getElementById('grid');
const viewer = document.getElementById('viewer');
const wrap = document.getElementById('canvas-wrap');
const playBtn = document.getElementById('play');
const scrub = document.getElementById('scrub');
const speedSel = document.getElementById('speed');

let renderer, scene, camera, controls, mixer, action, clip;
let playing = true;
const clock = new THREE.Clock();

function chips(ex) {
  return ex.primary.map(m => `<span class="chip primary">${m}</span>`).join('') +
    ex.secondary.map(m => `<span class="chip secondary">${m}</span>`).join('');
}

async function buildGrid() {
  const exercises = await (await fetch('exercises.json')).json();
  for (const ex of exercises) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <img src="${ex.thumb}" alt="${ex.name}" loading="lazy">
      <div class="meta">
        <h3>${ex.name}</h3>
        <small>${ex.equipment} · ${ex.difficulty}</small>
        <div class="chips">${chips(ex)}</div>
      </div>`;
    card.onclick = () => openViewer(ex);
    grid.appendChild(card);
  }
}

function initThree() {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  wrap.appendChild(renderer.domElement);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d10);
  scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x30343a, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(3, 5, 2);
  scene.add(sun);
  const floor = new THREE.GridHelper(6, 24, 0x2a323c, 0x1a2027);
  scene.add(floor);

  camera = new THREE.PerspectiveCamera(45, 1, 0.05, 50);
  camera.position.set(1.8, 1.5, 2.6);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.9, 0);
  controls.enableDamping = true;

  window.addEventListener('resize', resize);
  renderer.setAnimationLoop(tick);
}

function resize() {
  if (!renderer || !viewer.classList.contains('open')) return;
  const { clientWidth: w, clientHeight: h } = wrap;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function tick() {
  if (mixer && playing) {
    mixer.update(clock.getDelta() * Number(speedSel.value));
    scrub.value = Math.round((action.time / clip.duration) * 1000);
  } else {
    clock.getDelta();
  }
  controls.update();
  renderer.render(scene, camera);
}

async function openViewer(ex) {
  document.getElementById('viewer-title').textContent = ex.name;
  document.getElementById('viewer-muscles').innerHTML = chips(ex);
  document.getElementById('viewer-steps').innerHTML =
    (ex.steps || []).map(s => `<li>${s}</li>`).join('');
  renderBodymap(document.getElementById('viewer-body'), ex);
  viewer.classList.add('open');
  if (!renderer) initThree();
  resize();

  scene.children.filter(o => o.userData.exercise).forEach(o => scene.remove(o));
  const gltf = await new GLTFLoader().loadAsync(ex.glb);
  gltf.scene.userData.exercise = true;
  scene.add(gltf.scene);

  mixer = new THREE.AnimationMixer(gltf.scene);
  // play every clip — props (dumbbells/barbell) may export as their own
  // animation alongside the armature's; the longest clip drives the scrubber
  clip = gltf.animations.reduce((a, b) => (b.duration > a.duration ? b : a),
    gltf.animations[0]);
  let first;
  for (const c of gltf.animations) {
    const a = mixer.clipAction(c);
    a.setLoop(THREE.LoopRepeat).play();
    if (c === clip) first = a;
  }
  action = first;
  playing = true;
  playBtn.textContent = '⏸';
}

playBtn.onclick = () => {
  playing = !playing;
  playBtn.textContent = playing ? '⏸' : '▶';
};

scrub.oninput = () => {
  if (!action) return;
  playing = false;
  playBtn.textContent = '▶';
  action.time = (Number(scrub.value) / 1000) * clip.duration;
  mixer.update(0);
};

document.getElementById('close').onclick = () => viewer.classList.remove('open');

buildGrid();
