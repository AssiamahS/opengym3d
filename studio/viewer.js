// Adapted from OpenGym3D website/main.js, copyright 2026 SylvesterAssiamahGK, MIT.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const capture = new URLSearchParams(location.search).has('capture');
document.body.classList.toggle('capture', capture);
const wrap = document.querySelector('#canvas-wrap');
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:capture});
renderer.setPixelRatio(1);
wrap.prepend(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x10151c);
scene.add(new THREE.HemisphereLight(0xdfe8ff,0x30343a,1.6));
const sun = new THREE.DirectionalLight(0xffffff,2.2); sun.position.set(3,5,2); scene.add(sun);
scene.add(new THREE.GridHelper(6,30,0x526074,0x28303b));
const camera = new THREE.PerspectiveCamera(35,1,.01,50);
const controls = new OrbitControls(camera,renderer.domElement); controls.target.set(0,.85,0);
let mixer, actions=[],duration=0,time=0,playing=!capture;
const clock = new THREE.Clock();
function render(){controls.update();renderer.render(scene,camera);}
function resize(){renderer.setSize(wrap.clientWidth,wrap.clientHeight);camera.aspect=wrap.clientWidth/wrap.clientHeight;camera.updateProjectionMatrix();render();}
function view(name){const p={front:[0,1.0,3.6],side:[3.6,1.0,0],three:[2.4,1.3,2.8],rear:[0,1.0,-3.6]}[name];camera.position.set(...p);controls.target.set(0,.85,0);render();}
function seek(t){time=t;mixer.setTime(t);document.querySelector('#scrub').value=t/duration*1000;render();}
window.addEventListener('resize',resize); view('three');resize();
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'Pause':'Play';};
document.querySelector('#scrub').oninput=e=>{playing=false;document.querySelector('#play').textContent='Play';seek(Number(e.target.value)/1000*duration);};
try {
 const gltf=await new GLTFLoader().loadAsync('../outputs/bodyweight/squat-technical.glb');
 if(!gltf.animations.length) throw new Error('Missing animation');
 scene.add(gltf.scene);mixer=new THREE.AnimationMixer(gltf.scene);
 duration=Math.max(...gltf.animations.map(c=>c.duration));
 actions=gltf.animations.map(c=>mixer.clipAction(c).setLoop(THREE.LoopRepeat).play());
 document.querySelector('#status').textContent=`${gltf.animations.length} clip(s) · ${duration.toFixed(3)} s\nFinal GLB loaded. Drag to orbit.`;
 window.fms={ready:true,duration,seek,view,pause:()=>{playing=false;},trackTimes:()=>actions.map(a=>a.time),positions:()=>{const p={};gltf.scene.updateMatrixWorld(true);gltf.scene.traverse(o=>{if(o.isBone)p[o.name]=o.getWorldPosition(new THREE.Vector3()).toArray();});return p;},floor:()=>{let min=Infinity;const v=new THREE.Vector3();gltf.scene.updateMatrixWorld(true);gltf.scene.traverse(o=>{if(o.isSkinnedMesh){o.skeleton.update();for(let i=0;i<o.geometry.attributes.position.count;i++){o.getVertexPosition(i,v);v.applyMatrix4(o.matrixWorld);min=Math.min(min,v.y);}}});return min;}};
 seek(0);
 renderer.setAnimationLoop(()=>{const delta=clock.getDelta();if(playing)seek((time+delta*Number(document.querySelector('#speed').value))%duration);else render();});
} catch(e){document.querySelector('#status').textContent=`FAILED: ${e.message}`;window.fms={error:e.message};throw e;}
