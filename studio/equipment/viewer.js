// Bounded asset ownership: two cached assets, one serialized load, one active mixer.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const params=new URLSearchParams(location.search),capture=params.has('capture');
const output=params.has('baseline')?'baseline':params.get('output')||'library';
if(!['baseline','library'].includes(output))throw Error('Unknown equipment output');
const base=`../../outputs/${output==='baseline'?'equipment-use':'equipment-library'}/`;
document.body.classList.toggle('capture',capture);document.body.classList.add('gallery');
const wrap=document.querySelector('#canvas-wrap'),api=window.equipment={ready:false,mode:'gallery'};
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:capture});renderer.setPixelRatio(1);wrap.prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x121b26);scene.add(new THREE.HemisphereLight(0xe2edff,0x36312b,2));
for(const [position,intensity] of [[[3,5,4],2.7],[[-3,2,-3],1.3]]){const light=new THREE.DirectionalLight(0xffffff,intensity);light.position.set(...position);scene.add(light);}
const grid=new THREE.GridHelper(4,24,0x536175,0x293649);scene.add(grid);grid.visible=false;
const camera=new THREE.PerspectiveCamera(35,1,.005,30),controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=false;controls.addEventListener('change',()=>render());
const loader=new GLTFLoader(),cache=new Map(),CACHE_LIMIT=2,clock=new THREE.Clock();
let mode='gallery',model,mixer,actions=[],duration=0,start=0,phase=0,playing=false,catalog,variation,selectedId;
let serial=0,pending=null,loading=false,disposed=false,currentKey=null,activeMixers=0,loads=0,evictions=0,staleDisposals=0;
const safeFile=name=>{if(typeof name!=='string'||!/^[a-zA-Z0-9_-]+\.(glb|png|webp|jpg)$/.test(name))throw Error('Invalid catalog filename');return name;};
function render(){if(disposed||mode==='gallery')return;scene.updateMatrixWorld(true);renderer.render(scene,camera);}
function resize(){if(mode==='gallery')return;const w=wrap.clientWidth,h=wrap.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();render();}
function pause(){playing=false;document.querySelector('#play').textContent='Play';}
function detach(){pause();if(mixer){mixer.stopAllAction();mixer.uncacheRoot(model);mixer=undefined;activeMixers--;}actions=[];if(model)scene.remove(model);model=undefined;currentKey=null;}
function disposeAsset(asset){const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set();
 asset.scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const material of (Array.isArray(o.material)?o.material:o.material?[o.material]:[])){materials.add(material);for(const value of Object.values(material))if(value?.isTexture)textures.add(value);}if(o.skeleton)skeletons.add(o.skeleton);});
 skeletons.forEach(s=>s.dispose());geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());textures.forEach(t=>{t.dispose();t.source?.data?.close?.();});}
function trimCache(){while(cache.size>CACHE_LIMIT){const key=[...cache.keys()].find(k=>k!==currentKey);disposeAsset(cache.get(key));cache.delete(key);evictions++;}}
function view(name){if(mode==='gallery'||!model)return;
 if(name==='grip'&&mode==='demo'){pause();seek(0);camera.position.set(.65,1.35,1.3);controls.target.set(0,1.3,.2);controls.update();render();return;}
 if(mode==='demo'){const positions={front:[0,.97,3.6],side:[3.6,.97,0],three:[2.448,1.318,2.88]};camera.position.set(...positions[name]);controls.target.set(0,.85,0);controls.minDistance=.4;controls.maxDistance=8;}
 else{const box=new THREE.Box3().setFromObject(model),center=box.getCenter(new THREE.Vector3()),radius=Math.max(.01,box.getSize(new THREE.Vector3()).length()/2);
  const angle=Math.min(THREE.MathUtils.degToRad(camera.fov)/2,Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov)/2)*camera.aspect)),distance=radius/Math.sin(angle)*1.12;
  const direction={front:[0,.08,1],side:[1,.08,0],three:[.68,.32,.8]}[name];camera.position.copy(center).add(new THREE.Vector3(...direction).normalize().multiplyScalar(distance));controls.target.copy(center);controls.minDistance=radius*.7;controls.maxDistance=radius*20;camera.near=Math.max(.001,radius/100);camera.far=Math.max(30,radius*40);camera.updateProjectionMatrix();}
 controls.update();render();}
function seek(value){phase=Math.max(0,Math.min(1,value));if(mixer){for(const action of actions){action.enabled=true;action.paused=false;}mixer.setTime(start+phase*duration);}
 document.querySelector('#scrub').value=phase*1000;document.querySelector('#phase').textContent=phase<.05||phase>.95?'Setup / standing':phase<.45?'Descent':phase<.55?'Bottom transition':'Return to standing';
 document.querySelector('#direction').textContent=phase<.05||phase>.95?'Held setup':phase<.5?'↓ Lower':'↑ Return';render();}
function configure(){if(mode!=='inspect'||!model)return;const size=Number(document.querySelector('#size').value)/100;model.scale.setScalar(size);document.querySelector('#size-label').textContent=Math.round(size*100)+'%';const finish=document.querySelector('#finish').value;
 model.traverse(o=>{if(o.isMesh&&!o.userData.contact)for(const material of (Array.isArray(o.material)?o.material:[o.material])){material.userData.originalColor??=material.color.clone();material.color.copy(finish==='original'?material.userData.originalColor:new THREE.Color(finish==='steel'?0xb9c5d3:0x30343a));}});view('three');}
function metadata(item){document.querySelector('#equipment-name').textContent=item.name;document.querySelector('#description').textContent=item.description;const dimensions=document.querySelector('#dimensions');dimensions.replaceChildren();
 for(const [key,value] of Object.entries(item.dimensions||{})){const term=document.createElement('dt'),text=document.createElement('dd');term.textContent=key.replace(/([A-Z])/g,' $1');text.textContent=typeof value==='number'?`${(value*1000).toFixed(1)} mm`:String(value);dimensions.append(term,text);}
 const config=item.configuration||{};document.querySelector('#configuration').textContent=`Inspection scale ${Math.round((config.scale?.min??.8)*100)}–${Math.round((config.scale?.max??1.2)*100)}%. Original, bright steel or dark appearance. ${config.massKg==null?'No load rating is specified.':`Recorded mass: ${config.massKg} kg.`} Demonstration dimensions remain fixed.`;
 document.querySelector('#contact-list').replaceChildren(...(item.contactPoints||[]).map(p=>{const li=document.createElement('li');li.textContent=`${p.id} · ${p.kind} · [${p.position.map(v=>(v*1000).toFixed(1)).join(', ')}] mm`;return li;}));
 document.querySelector('#provenance').textContent=`${item.provenance?.source||'Procedurally generated geometry'}. License: ${item.license}. `;
 if(/^licenses\/[a-zA-Z0-9_.-]+$/.test(item.provenance?.licensePath||'')){const link=document.createElement('a');link.href=base+item.provenance.licensePath;link.textContent=' Read license';document.querySelector('#provenance').append(link);}
 if(/^pipeline\/[a-zA-Z0-9_.-]+\.py$/.test(item.provenance?.sourcePath||'')){const link=document.createElement('a');link.href='../../'+item.provenance.sourcePath;link.textContent=' · Generator source';document.querySelector('#provenance').append(link);}const provenanceLink=document.createElement('a');provenanceLink.href=base+(output==='baseline'?'equipment.json':'catalog.json');provenanceLink.textContent=' · Full provenance';document.querySelector('#provenance').append(provenanceLink);
 const range=item.configuration?.scale;document.querySelector('#size').min=String((range?.min??.8)*100);document.querySelector('#size').max=String((range?.max??1.2)*100);
 const compatible=item.id==='dumbbell'&&(item.compatibleVariations||[]).includes('goblet-squat-experimental');document.querySelector('#choose-demo').hidden=!compatible;document.querySelector('#no-demo').hidden=compatible;document.querySelector('#demo').disabled=!compatible;}
function addMarkers(asset,item){if(asset.scene.userData.markers)return;const markers=new THREE.Group();markers.name='inspection-contact-markers';for(const point of item.contactPoints||[]){const dot=new THREE.Mesh(new THREE.SphereGeometry(.007,12,8),new THREE.MeshBasicMaterial({color:0xff9d47}));dot.position.fromArray(point.position);dot.userData.contact=true;dot.name=point.id;markers.add(dot);}asset.scene.add(markers);asset.scene.userData.markers=markers;}
function activate(asset,request){detach();model=asset.scene;scene.add(model);currentKey=request.key;mode=request.mode;selectedId=request.id;document.body.classList.remove('gallery');grid.visible=mode==='demo';document.querySelector('#gallery-back').hidden=false;
 const item=catalog.items.find(i=>i.id===selectedId);metadata(item);document.querySelectorAll('#catalog button').forEach(b=>b.setAttribute('aria-pressed',String(b.id===selectedId)));
 if(mode==='demo'){if(!asset.animations.length)throw Error('Demonstration has no animation');mixer=new THREE.AnimationMixer(model);activeMixers++;start=Math.min(...asset.animations.flatMap(c=>c.tracks.map(t=>t.times[0])));duration=Math.max(...asset.animations.map(c=>c.duration))-start;actions=asset.animations.map(c=>{const a=mixer.clipAction(c).setLoop(THREE.LoopOnce,1);a.clampWhenFinished=true;return a.play();});camera.near=.005;camera.far=30;}
 else{addMarkers(asset,item);document.querySelector('#size').value='100';document.querySelector('#finish').value='original';model.scale.setScalar(1);model.userData.markers.visible=document.querySelector('#contacts').checked;}
 for(const id of ['play','scrub','speed-wrap','guidance','grip-view'])document.getElementById(id).hidden=mode!=='demo';document.querySelector('#inspection').hidden=mode!=='inspect';document.querySelector('#direction').hidden=mode!=='demo'||!document.querySelector('#indicators').checked;
 document.querySelector('#inspect').setAttribute('aria-pressed',String(mode==='inspect'));document.querySelector('#demo').setAttribute('aria-pressed',String(mode==='demo'));
 resize();if(mode==='inspect')configure();seek(0);view('three');document.querySelector('#status').textContent=mode==='demo'?`Experimental interaction proof · ${duration.toFixed(3)} s loop · drag to orbit`:`${item.name} · drag to rotate · orange contact frames`;
 Object.assign(api,{ready:true,error:null,mode,duration,start,selectedId});}
async function pump(){if(loading)return;loading=true;try{while(pending){const request=pending;pending=null;let asset,fromCache=false;try{asset=cache.get(request.key);fromCache=!!asset;if(!asset){loads++;asset=await loader.loadAsync(base+request.file);}
 if(disposed||request.token!==serial){if(!fromCache){disposeAsset(asset);staleDisposals++;}request.resolve(false);continue;}
 cache.delete(request.key);cache.set(request.key,asset);activate(asset,request);trimCache();api.lastSelection={id:request.id,mode:request.mode,cacheHit:fromCache,elapsed_ms:performance.now()-request.startedAt,method:'Selection request to parsed scene setup and first render submission; excludes GPU completion'};document.querySelector('#loading').hidden=true;request.resolve(true);
 }catch(error){if(asset&&!cache.has(request.key))disposeAsset(asset);if(request.token===serial&&!disposed){detach();api.error=error.message;api.ready=false;document.querySelector('#loading').hidden=true;document.querySelector('#status').textContent='FAILED: '+error.message;request.reject(error);}else request.resolve(false);}}}finally{loading=false;}}
function select(id,next='inspect'){if(disposed)return Promise.reject(Error('Viewer has been disposed'));const item=catalog?.items.find(i=>i.id===id);if(!item)return Promise.reject(Error('Unknown equipment'));if(next==='demo'&&(id!=='dumbbell'||!item.compatibleVariations.includes('goblet-squat-experimental')))return Promise.reject(Error('No compatible demonstration'));
 const token=++serial;pending?.resolve(false);detach();mode='loading';api.ready=false;api.error=null;document.body.classList.remove('gallery');document.querySelector('#loading').hidden=false;
 const file=next==='demo'?'goblet.glb':safeFile(item.geometry);return new Promise((resolve,reject)=>{pending={token,id,mode:next,key:next==='demo'?'demo:goblet':`inspect:${id}`,file,startedAt:performance.now(),resolve,reject};pump();});}
function switchMode(next){return select(selectedId||'dumbbell',next);}
function gallery(){serial++;pending?.resolve(false);pending=null;detach();mode='gallery';grid.visible=false;api.ready=true;api.mode='gallery';document.body.classList.add('gallery');document.querySelector('#gallery-back').hidden=true;document.querySelector('#loading').hidden=true;}
function dispose(){if(disposed)return;disposed=true;serial++;pending?.resolve(false);pending=null;detach();cache.forEach(disposeAsset);cache.clear();grid.geometry.dispose();for(const material of (Array.isArray(grid.material)?grid.material:[grid.material]))material.dispose();renderer.setAnimationLoop(null);controls.dispose();renderer.renderLists.dispose();renderer.dispose();api.ready=false;}
Object.assign(api,{select,switchMode,gallery,seek,view,pause,configure,dispose,
 state:()=>({mode,selectedId,phase,playing,camera:camera.position.toArray(),target:controls.target.toArray(),scale:mode==='inspect'?model?.scale.x:undefined,contacts:model?.userData.markers?.visible,times:actions.map(a=>a.time)}),
 resources:()=>({cacheKeys:[...cache.keys()],cacheLimit:CACHE_LIMIT,activeMixers,loads,evictions,staleDisposals,loading,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,programs:renderer.info.programs?.length||0,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles}),
 gpu:()=>{const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');return{vendor:gl.getParameter(gl.VENDOR),renderer:gl.getParameter(gl.RENDERER),unmaskedRenderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):null};},
 positions:()=>{const values={};model?.updateMatrixWorld(true);model?.traverse(o=>{if(o.isBone||/grip|contact|dumbbell/i.test(o.name))values[o.name]=o.getWorldPosition(new THREE.Vector3()).toArray();});return values;}});
document.querySelector('#gallery-back').onclick=gallery;document.querySelector('#inspect').onclick=()=>switchMode('inspect');for(const id of ['demo','choose-demo'])document.getElementById(id).onclick=()=>switchMode('demo');
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));document.querySelector('#play').onclick=()=>{playing=!playing;clock.getDelta();document.querySelector('#play').textContent=playing?'Pause':'Play';};
document.querySelector('#scrub').oninput=e=>{pause();seek(Number(e.target.value)/1000);};document.querySelector('#setup-view').onclick=()=>{pause();seek(0);view('three');};for(const id of ['size','finish'])document.getElementById(id).oninput=configure;
document.querySelector('#contacts').onchange=e=>{if(mode==='inspect'&&model){model.userData.markers.visible=e.target.checked;render();}};
document.querySelector('#indicators').onchange=e=>document.querySelector('#direction').hidden=!e.target.checked||mode!=='demo';document.querySelector('#form').onchange=e=>document.querySelector('#form-text').hidden=!e.target.checked;
window.addEventListener('resize',resize);window.addEventListener('pagehide',dispose);window.addEventListener('pageshow',event=>{if(event.persisted&&disposed)location.reload();});
try{const get=async file=>{const r=await fetch(base+file);if(!r.ok)throw Error('Missing '+file);return r.json();};
 [catalog,variation]=await Promise.all([output==='baseline'?get('equipment.json').then(item=>({schema:'equipment-catalog/1',items:[{...item,geometry:'dumbbell.glb',thumbnail:'inspection.png'}]})):get('catalog.json'),get('variation.json')]);
 if(catalog.schema!=='equipment-catalog/1'||!Array.isArray(catalog.items)||new Set(catalog.items.map(i=>i.id)).size!==catalog.items.length)throw Error('Invalid catalog');
 for(const item of catalog.items){if(!/^[a-z0-9-]+$/.test(item.id))throw Error('Invalid catalog id');safeFile(item.geometry);const card=document.createElement('button');card.id=item.id;card.className='card';card.setAttribute('aria-pressed','false');const img=document.createElement('img');img.src=base+safeFile(item.thumbnail);img.alt='';img.width=300;img.height=180;const title=document.createElement('strong');title.textContent=item.name;const caption=document.createElement('span');caption.textContent=item.compatibleVariations?.length?'Inspection + experimental demonstration':'Equipment inspection';card.append(img,title,caption);card.onclick=()=>select(item.id);document.querySelector('#catalog').append(card);}
 const statuses=document.querySelector('#approval-status');for(const [key,label] of [['technical','Technical'],['visual','Visual'],['movement','Movement'],['humanApproval','Human approval']]){const term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;value.textContent=variation[key]||'Not verified';statuses.append(term,value);}
 if(variation.setupSteps?.length)document.querySelector('#setup').replaceChildren(...variation.setupSteps.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
 document.querySelector('#glb-link').href=base+'goblet.glb';document.querySelector('#report-link').href=base+'contact-validation.json';document.querySelector('.preview-link').href=`preview.html?output=${output}`;
 api.items=catalog.items.map(i=>i.id);api.output=output;api.ready=true;
 if(params.has('demo')||capture)await select('dumbbell','demo');
 renderer.setAnimationLoop(()=>{const delta=clock.getDelta();if(playing&&mode==='demo')seek((phase+delta*Number(document.querySelector('#speed').value)/duration)%1);});
}catch(error){api.error=error.message;document.querySelector('#status').textContent='FAILED: '+error.message;throw error;}
