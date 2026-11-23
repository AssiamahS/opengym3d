// Read-only browser inspection of new assets. Never writes the previous proof.
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
const out=process.env.FMS_EQUIPMENT_OUTPUT||'outputs/equipment-library';
if(out!=='outputs/equipment-library')throw Error('Catalog checks only write the new output');
const hash=async path=>createHash('sha256').update(await readFile(path)).digest('hex');
const files=['catalog.json','dumbbell.glb','kettlebell.glb','barbell.glb','goblet.glb'];
const initial=Object.fromEntries(await Promise.all(files.map(async name=>[name,await hash(out+'/'+name)])));
const report={status:'FAIL',errors:[],screenshots:[],resource_cycles:[],file_sha256:{},catalog_sha256:initial['catalog.json'],glb_sha256:initial['goblet.glb'],asset_sha256:initial};
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
let browser;
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(Error('Server exit '+c)));});
 browser=await chromium.launch({channel:'chromium',args:['--use-angle=d3d11']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),requests=[];page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>requests.push(r.url()));
 const url=`http://127.0.0.1:${port}/studio/equipment/`;
 await page.goto(url);await page.waitForFunction(()=>window.equipment?.ready||window.equipment?.error);
 if(await page.evaluate(()=>window.equipment.error))throw Error(await page.evaluate(()=>window.equipment.error));
 await page.locator('#catalog img').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
 if(requests.some(u=>u.endsWith('.glb')))throw Error('Gallery eagerly loaded a GLB');
 const initialState=await page.evaluate(()=>window.equipment.resources());if(initialState.loads!==0||initialState.cacheKeys.length)throw Error('Gallery owns unexpected model assets');
 report.cold_gallery=await page.evaluate(()=>({ready_ms:performance.now(),resources:performance.getEntriesByType('resource').map(r=>({url:r.name,transfer_bytes:r.transferSize,encoded_bytes:r.encodedBodySize,duration_ms:r.duration})),state:window.equipment.resources()}));
 report.cold_gallery.glb_requests=0;await page.screenshot({path:out+'/gallery.png',fullPage:true});report.screenshots.push(out+'/gallery.png');
 // Delayed stale load and rapid clicks must never activate the wrong selection.
 await page.route('**/barbell.glb',async route=>{await new Promise(resolve=>setTimeout(resolve,180));await route.continue();});
 report.race_results=await page.evaluate(()=>Promise.all([window.equipment.select('barbell'),window.equipment.select('kettlebell'),window.equipment.select('dumbbell')]));
 const race=await page.evaluate(()=>({state:window.equipment.state(),resources:window.equipment.resources()}));
 if(race.state.selectedId!=='dumbbell'||race.state.mode!=='inspect'||race.resources.staleDisposals<1)throw Error('Rapid selection race failed');report.race=race;await page.unroute('**/barbell.glb');
 for(const id of ['dumbbell','kettlebell','barbell']){
  const begin=Date.now();await page.locator('#'+id).click();await page.waitForFunction(id=>window.equipment.ready&&window.equipment.state().selectedId===id,id);
  const selection=await page.evaluate(()=>window.equipment.lastSelection);
  await page.locator('#size').fill('110');await page.locator('#size').dispatchEvent('input');await page.locator('#finish').selectOption('steel');await page.locator('#finish').dispatchEvent('input');
  const s=await page.evaluate(()=>window.equipment.state());if(Math.abs(s.scale-1.1)>1e-8)throw Error('Configuration failed '+id);
  const before=s.camera,box=await page.locator('canvas').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+70,box.y+box.height/2+25,{steps:7});await page.mouse.up();
  if(JSON.stringify(before)===JSON.stringify((await page.evaluate(()=>window.equipment.state())).camera))throw Error('Orbit failed '+id);
  if(id!=='dumbbell'&&(!await page.locator('#demo').isDisabled()||!await page.locator('#choose-demo').isHidden()))throw Error('Unsupported equipment offers demonstration');
  await page.locator('#size').fill('100');await page.locator('#size').dispatchEvent('input');await page.locator('#finish').selectOption('original');await page.locator('#finish').dispatchEvent('input');
  await page.screenshot({path:`${out}/catalog-${id}.png`,fullPage:true});report.screenshots.push(`${out}/catalog-${id}.png`);report[id]={complete_inspection_workflow_ms:Date.now()-begin,selection,state:await page.evaluate(()=>window.equipment.state())};
 }
 for(let cycle=0;cycle<4;cycle++){
  for(const id of ['dumbbell','kettlebell','barbell']){await page.evaluate(id=>window.equipment.select(id),id);const r=await page.evaluate(()=>window.equipment.resources());if(r.cacheKeys.length>2||r.activeMixers!==0)throw Error('Inspection resources exceeded ownership bound');}
  await page.evaluate(()=>window.equipment.select('dumbbell','demo'));const first=await page.evaluate(()=>window.equipment.resources());
  await page.evaluate(()=>window.equipment.switchMode('demo'));const second=await page.evaluate(()=>window.equipment.resources());
  if(second.activeMixers!==1||second.loads!==first.loads||second.cacheKeys.length>2)throw Error('Repeated demo leaks mixer or reloads cached GLB');
  report.resource_cycles.push(second);
 }
 const last=report.resource_cycles.at(-1),warm=report.resource_cycles[1];if(last.geometries>warm.geometries||last.textures>warm.textures||last.programs>warm.programs)throw Error('GPU resource counts grew over repeated full cycles');
 report.gpu=await page.evaluate(()=>window.equipment.gpu());
 report.frame_intervals=await page.evaluate(async()=>{const times=[];let previous;for(let i=0;i<68;i++){await new Promise(requestAnimationFrame);const now=performance.now();if(i>=8)times.push(now-previous);previous=now;window.equipment.seek((i%60)/60);}times.sort((a,b)=>a-b);return{samples:60,median_ms:times[30],p95_ms:times[57],method:'8 warmup + 60 headless animation-frame intervals with seek/render; no readback; not displayed-device FPS'};});
 await page.locator('#setup-view').click();await page.locator('#grip-view').click();await page.locator('#canvas-wrap').screenshot({path:out+'/grip-after.png'});report.screenshots.push(out+'/grip-after.png');
 await page.evaluate(()=>{const w=document.querySelector('#canvas-wrap');w.style.width='320px';w.style.height='320px';window.dispatchEvent(new Event('resize'));window.equipment.view('grip');});
 await page.locator('#canvas-wrap').screenshot({path:out+'/grip-after-320.png'});report.screenshots.push(out+'/grip-after-320.png');
 // Exact same preset and phase on preserved old geometry; output still new directory.
 await page.goto(url+'?baseline&demo');await page.waitForFunction(()=>window.equipment?.ready||window.equipment?.error);await page.locator('#grip-view').click();await page.locator('#canvas-wrap').screenshot({path:out+'/grip-before.png'});report.screenshots.push(out+'/grip-before.png');
 await page.evaluate(()=>{const w=document.querySelector('#canvas-wrap');w.style.width='320px';w.style.height='320px';window.dispatchEvent(new Event('resize'));window.equipment.view('grip');});await page.locator('#canvas-wrap').screenshot({path:out+'/grip-before-320.png'});report.screenshots.push(out+'/grip-before-320.png');
 await page.evaluate(()=>window.equipment.dispose());report.disposed=await page.evaluate(()=>window.equipment.resources());if(report.disposed.cacheKeys.length||report.disposed.activeMixers!==0||report.disposed.geometries!==0||report.disposed.textures!==0)throw Error('Explicit disposal retained assets, mixer or GPU allocations');
 // Teardown while the only loader is in flight must release its late result.
 await page.goto(url);await page.waitForFunction(()=>window.equipment?.ready);await page.route('**/barbell.glb',async route=>{await new Promise(resolve=>setTimeout(resolve,180));await route.continue();});
 const lateResult=await page.evaluate(async()=>{const selected=window.equipment.select('barbell');window.equipment.dispose();return selected;});
 report.pending_load_disposed=await page.evaluate(()=>window.equipment.resources());await page.unroute('**/barbell.glb');
 if(lateResult!==false||report.pending_load_disposed.staleDisposals!==1||report.pending_load_disposed.cacheKeys.length||report.pending_load_disposed.activeMixers||report.pending_load_disposed.geometries||report.pending_load_disposed.textures)throw Error('Late load survived page teardown');
 // Navigate through the actual lightweight link and back to a different item.
 await page.goto(url);await page.waitForFunction(()=>window.equipment?.ready);await page.locator('.preview-link').click();await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2);report.quick_peek_navigation={path:new URL(page.url()).pathname,width:await page.locator('video').evaluate(v=>v.videoWidth)};if(report.quick_peek_navigation.width!==320)throw Error('Quick Peek is not a 320px asset');
 await page.goBack();await page.waitForFunction(()=>window.equipment?.ready);await page.locator('#kettlebell').click();await page.waitForFunction(()=>window.equipment.ready&&window.equipment.state().selectedId==='kettlebell');report.return_navigation=await page.evaluate(()=>window.equipment.state());
 for(const name of files)if(await hash(out+'/'+name)!==initial[name])throw Error('Asset changed during catalog check: '+name);
 for(const name of ['index.html','style.css','viewer.js','preview.html'])report.file_sha256['studio/equipment/'+name]=await hash('studio/equipment/'+name);
 for(const name of ['studio/equipment_capture.mjs','studio/equipment_catalog_check.mjs'])report.file_sha256[name]=await hash(name);
 if(report.errors.length)throw Error(report.errors.join('\n'));report.status='PASS';report.browser=browser.version();
}catch(error){report.errors.push(error.stack);throw error;}finally{await writeFile(out+'/catalog-check.json',JSON.stringify(report,null,2));await browser?.close();server.kill();}
