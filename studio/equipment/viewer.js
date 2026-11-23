// Reuse the pinned local Three.js viewer; geometry and animation remain independent assets.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const params=new URLSearchParams(location.search),capture=params.has('capture');
document.body.classList.toggle('capture',capture);
const base='../../outputs/equipment-use/',wrap=document.querySelector('#canvas-wrap');
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:capture});renderer.setPixelRatio(1);wrap.prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x121b26);
scene.add(new THREE.HemisphereLight(0xe2edff,0x36312b,2));
const sun=new THREE.DirectionalLight(0xffffff,2.7);sun.position.set(3,5,4);scene.add(sun);
const fill=new THREE.DirectionalLight(0xe0eaff,1.3);fill.position.set(-3,2,-3);scene.add(fill);
const grid=new THREE.GridHelper(4,24,0x536175,0x293649);scene.add(grid);
const camera=new THREE.PerspectiveCamera(35,1,.005,30),controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=false;controls.addEventListener('change',()=>renderer.render(scene,camera));
let mode='inspect',model,mixer,actions=[],duration=0,start=0,phase=0,playing=false,metadata,variation;
let inspection,demo,request=0;const clock=new THREE.Clock();const api=window.equipment={ready:false};
function render(){scene.updateMatrixWorld(true);renderer.render(scene,camera);}
function resize(){renderer.setSize(wrap.clientWidth,wrap.clientHeight);camera.aspect=wrap.clientWidth/wrap.clientHeight;camera.updateProjectionMatrix();render();}
function view(name){if(name==='grip'&&mode==='demo'){pause();seek(0);camera.position.set(.65,1.35,1.3);controls.target.set(0,1.3,.2);controls.update();render();return;}
 const isDemo=mode==='demo',distance=isDemo?3.6:.65,target=isDemo?.85:0;
 const positions={front:[0,target+.12,distance],side:[distance,target+.12,0],three:[distance*.68,target+distance*.13,distance*.8]};
 camera.position.set(...positions[name]);controls.target.set(0,target,0);controls.minDistance=isDemo?.4:.1;controls.maxDistance=isDemo?8:2;controls.update();render();}
function seek(value){phase=Math.max(0,Math.min(1,value));if(mixer){for(const action of actions){action.enabled=true;action.paused=false;}mixer.setTime(start+phase*duration);}
 document.querySelector('#scrub').value=phase*1000;
 const label=phase<.05||phase>.95?'Setup / standing':phase<.45?'Descent':phase<.55?'Bottom transition':'Return to standing';
 document.querySelector('#phase').textContent=label;
 document.querySelector('#direction').textContent=phase<.05||phase>.95?'Held setup':phase<.5?'↓ Lower':'↑ Return';render();}
function pause(){playing=false;document.querySelector('#play').textContent='Play';}
function configure(){if(!inspection)return;const size=Number(document.querySelector('#size').value)/100;inspection.scene.scale.setScalar(size);document.querySelector('#size-label').textContent=Math.round(size*100)+'%';
 const finish=document.querySelector('#finish').value;inspection.scene.traverse(o=>{if(o.isMesh&&!o.userData.contact){if(!o.userData.originalColor)o.userData.originalColor=o.material.color.clone();o.material.color.copy(finish==='original'?o.userData.originalColor:new THREE.Color(finish==='steel'?0xb9c5d3:0x30343a));}});render();}
async function switchMode(next){const token=++request;pause();api.ready=false;document.querySelector('#status').textContent='Loading…';
 try{let asset;if(next==='inspect'){inspection??=await new GLTFLoader().loadAsync(base+'dumbbell.glb');asset=inspection;}else{demo??=await new GLTFLoader().loadAsync(base+'goblet.glb');asset=demo;}
 if(token!==request)return;if(model)scene.remove(model);model=asset.scene;scene.add(model);mode=next;grid.visible=next==='demo';
 mixer=undefined;actions=[];if(next==='demo'){if(!asset.animations.length)throw Error('Demonstration has no animation');mixer=new THREE.AnimationMixer(model);start=Math.min(...asset.animations.flatMap(c=>c.tracks.map(t=>t.times[0])));duration=Math.max(...asset.animations.map(c=>c.duration))-start;
 actions=asset.animations.map(c=>{const a=mixer.clipAction(c).setLoop(THREE.LoopOnce,1);a.clampWhenFinished=true;return a.play();});}
 if(next==='inspect'&&!model.userData.markers){const markers=new THREE.Group();markers.name='inspection-contact-markers';for(const point of metadata.contactPoints||[]){const dot=new THREE.Mesh(new THREE.SphereGeometry(.007,12,8),new THREE.MeshBasicMaterial({color:0xff9d47}));dot.position.fromArray(point.position);dot.userData.contact=true;dot.name=point.id;markers.add(dot);}model.add(markers);model.userData.markers=markers;}
 for(const id of ['play','scrub','speed-wrap','guidance','grip-view'])document.getElementById(id).hidden=next!=='demo';document.querySelector('#inspection').hidden=next!=='inspect';
 document.querySelector('#direction').hidden=next!=='demo'||!document.querySelector('#indicators').checked;
 document.querySelector('#inspect').setAttribute('aria-pressed',String(next==='inspect'));document.querySelector('#demo').setAttribute('aria-pressed',String(next==='demo'));
 if(next==='inspect'){configure();model.userData.markers.visible=document.querySelector('#contacts').checked;}seek(0);view('three');resize();
 document.querySelector('#status').textContent=next==='demo'?`Experimental interaction proof · ${duration.toFixed(3)} s loop · drag to orbit`:'Standalone dumbbell · drag to rotate · orange contact frames';
 Object.assign(api,{ready:true,mode,duration,start});
 }catch(error){api.error=error.message;document.querySelector('#status').textContent='FAILED: '+error.message;throw error;}}
Object.assign(api,{switchMode,seek,view,pause,configure,state:()=>({mode,phase,playing,camera:camera.position.toArray(),scale:inspection?.scene.scale.x,contacts:inspection?.scene.userData.markers?.visible,times:actions.map(a=>a.time)}),positions:()=>{const values={};model?.updateMatrixWorld(true);model?.traverse(o=>{if(o.isBone||/grip|contact|dumbbell/i.test(o.name))values[o.name]=o.getWorldPosition(new THREE.Vector3()).toArray();});return values;}});
document.querySelector('#dumbbell').onclick=()=>switchMode('inspect');document.querySelector('#inspect').onclick=()=>switchMode('inspect');
for(const id of ['demo','choose-demo'])document.getElementById(id).onclick=()=>switchMode('demo');
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'Pause':'Play';};
document.querySelector('#scrub').oninput=e=>{pause();seek(Number(e.target.value)/1000);};
document.querySelector('#setup-view').onclick=()=>{pause();seek(0);view('three');};
for(const id of ['size','finish'])document.getElementById(id).oninput=configure;
document.querySelector('#contacts').onchange=e=>{if(inspection)inspection.scene.userData.markers.visible=e.target.checked;render();};
document.querySelector('#indicators').onchange=e=>document.querySelector('#direction').hidden=!e.target.checked||mode!=='demo';
document.querySelector('#form').onchange=e=>document.querySelector('#form-text').hidden=!e.target.checked;
window.addEventListener('resize',resize);
try{[metadata,variation]=await Promise.all(['equipment.json','variation.json'].map(async file=>{const r=await fetch(base+file);if(!r.ok)throw Error('Missing '+file);return r.json();}));
 document.querySelector('#description').textContent=metadata.description;
 const statuses=document.querySelector('#approval-status');for(const [key,label] of [['technical','Technical'],['visual','Visual'],['movement','Movement'],['humanApproval','Human approval']]){const term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;value.textContent=variation[key]||'Not verified';statuses.append(term,value);}
 if(variation.setupSteps?.length){document.querySelector('#setup').replaceChildren(...variation.setupSteps.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));}
 await switchMode(params.has('demo')||capture?'demo':'inspect');
 renderer.setAnimationLoop(()=>{const delta=clock.getDelta();if(playing&&mode==='demo')seek((phase+delta*Number(document.querySelector('#speed').value)/duration)%1);else render();});
}catch(error){api.error=error.message;document.querySelector('#status').textContent='FAILED: '+error.message;throw error;}
