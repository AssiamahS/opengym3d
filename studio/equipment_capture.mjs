// Actual catalog interactions and final-GLB capture. No alternative animation.
import {chromium} from 'playwright';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
const out=process.env.FMS_EQUIPMENT_OUTPUT||'outputs/equipment-library',previewOnly=process.argv.includes('--preview-only'),gripOnly=process.argv.includes('--grip-only');
if(out!=='outputs/equipment-library')throw Error('Capture writes only the new equipment-library output; baseline is read-only');
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
let browser;const report={status:'FAIL',errors:[],screenshots:[]};
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(Error(`Server exit ${c}`)));});
 browser=await chromium.launch({channel:'chromium',args:['--use-angle=d3d11']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>report.errors.push(e.message));
 const root=`http://127.0.0.1:${port}/studio/equipment/`;
 if(gripOnly){
  await page.goto(root+'?demo&output=library');await page.waitForFunction(()=>window.equipment?.ready||window.equipment?.error);
  if(await page.evaluate(()=>window.equipment.error))throw Error(await page.evaluate(()=>window.equipment.error));
  await page.locator('#grip-view').click();await page.locator('#canvas-wrap').screenshot({path:out+'/grip-detail.png'});report.screenshots.push(out+'/grip-detail.png');
 }else if(previewOnly){
  const requests=[];page.on('request',r=>requests.push(r.url()));await page.goto(root+'preview.html?output=library');
  await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
  await page.locator('video').evaluate(v=>v.play());await page.waitForTimeout(500);
  if(await page.locator('video').evaluate(v=>v.currentTime<=0||!v.loop||v.clientWidth!==320||v.videoWidth!==320||v.videoHeight!==320))throw Error('Quick Peek playback, loop or dimensions failed');
  await page.screenshot({path:out+'/quick-peek.png'});
  await page.locator('[data-view=side]').click();await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
  if(await page.locator('video').evaluate(v=>v.videoWidth!==320||v.videoHeight!==320))throw Error('Side Quick Peek dimensions failed');
  if(requests.some(u=>/\.glb|three\.module|viewer\.js/.test(u)))throw Error('Lightweight preview requested 3D assets');
  report.requests=requests;report.screenshots.push(out+'/quick-peek.png');report.file_sha256={};
  for(const file of [out+'/quick-front.mp4',out+'/quick-side.mp4','studio/equipment/preview.html'])report.file_sha256[file]=createHash('sha256').update(await readFile(file)).digest('hex');
 }else{
  const initialHash=createHash('sha256').update(await readFile(out+'/goblet.glb')).digest('hex');
  await page.goto(root);await page.waitForFunction(()=>window.equipment?.ready||window.equipment?.error);
  if(await page.evaluate(()=>window.equipment.error))throw Error(await page.evaluate(()=>window.equipment.error));
  await page.locator('#dumbbell').click();await page.waitForFunction(()=>window.equipment.ready&&window.equipment.mode==='inspect');
  await page.locator('#size').fill('110');await page.locator('#size').dispatchEvent('input');await page.locator('#finish').selectOption('steel');await page.locator('#finish').dispatchEvent('input');
  if(Math.abs((await page.evaluate(()=>window.equipment.state())).scale-1.1)>1e-6)throw Error('Inspection configuration did not apply');
  await page.locator('#contacts').uncheck();if((await page.evaluate(()=>window.equipment.state())).contacts)throw Error('Contact markers failed to hide');await page.locator('#contacts').check();
  const before=await page.evaluate(()=>window.equipment.state().camera),box=await page.locator('canvas').boundingBox();
  await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+100,box.y+box.height/2+30,{steps:10});await page.mouse.up();
  if(JSON.stringify(before)===JSON.stringify(await page.evaluate(()=>window.equipment.state().camera)))throw Error('Inspection orbit failed');
  await page.screenshot({path:out+'/inspection.png'});report.screenshots.push(out+'/inspection.png');
  await page.locator('#choose-demo').click();await page.waitForFunction(()=>window.equipment.ready&&window.equipment.mode==='demo');
  if(await page.evaluate(()=>window.equipment.error))throw Error(await page.evaluate(()=>window.equipment.error));
  await page.locator('#setup-view').click();await page.screenshot({path:out+'/setup.png'});report.screenshots.push(out+'/setup.png');
  await page.locator('#grip-view').click();await page.locator('#canvas-wrap').screenshot({path:out+'/grip-detail.png'});report.screenshots.push(out+'/grip-detail.png');await page.evaluate(()=>window.equipment.view('three'));
  await page.locator('#scrub').fill('500');await page.locator('#scrub').dispatchEvent('input');
  if(Math.abs((await page.evaluate(()=>window.equipment.state())).phase-.5)>1e-8)throw Error('Scrub failed');
  await page.locator('#form').check();await page.locator('#indicators').uncheck();
  if(!(await page.locator('#direction').isHidden())||!(await page.locator('#form-text').isVisible()))throw Error('Guidance toggles failed');
  await page.locator('#play').click();await page.waitForTimeout(450);const advanced=await page.evaluate(()=>window.equipment.state());await page.evaluate(()=>window.equipment.pause());
  if(advanced.phase===.5)throw Error('Demo playback did not advance');
  const demoBefore=await page.evaluate(()=>window.equipment.state().camera);
  await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2-90,box.y+box.height/2,{steps:8});await page.mouse.up();
  if(JSON.stringify(demoBefore)===JSON.stringify(await page.evaluate(()=>window.equipment.state().camera)))throw Error('Demo orbit failed');
  await page.goto(root+'?capture&demo&output=library');await page.waitForFunction(()=>window.equipment?.ready||window.equipment?.error);
  const duration=await page.evaluate(()=>window.equipment.duration),fps=30,count=Math.round(duration*fps);if(!(duration>0&&count>0))throw Error('Missing motion interval');
  const samples=[];
  for(const view of ['front','side']){
   await mkdir(`${out}/frames-${view}`,{recursive:true});await page.evaluate(v=>window.equipment.view(v),view);
   for(let i=0;i<count;i++){await page.evaluate(p=>window.equipment.seek(p),i/count);await page.locator('#canvas-wrap').screenshot({path:`${out}/frames-${view}/${String(i).padStart(4,'0')}.png`});if(view==='front'&&i%15===0)samples.push({phase:i/count,positions:await page.evaluate(()=>window.equipment.positions())});}
   for(const [name,phase] of [['standing',0],['descent',.25],['bottom',.5]]){await page.evaluate(p=>window.equipment.seek(p),phase);const path=`${out}/${view}-${name}.png`;await page.locator('#canvas-wrap').screenshot({path});report.screenshots.push(path);}
  }
  for(const phase of [0,.25,.5,.75,1,.123,.337]){await page.evaluate(p=>window.equipment.seek(p),phase);samples.push({phase,positions:await page.evaluate(()=>window.equipment.positions())});}
  if(samples.some(s=>Object.values(s.positions).some(p=>p.length!==3||p.some(v=>!Number.isFinite(v)))))throw Error('Non-finite exported node sample');
  const finalHash=createHash('sha256').update(await readFile(out+'/goblet.glb')).digest('hex');if(initialHash!==finalHash)throw Error('GLB changed during capture; rerun after export completes');
  Object.assign(report,{duration,fps,frame_count:count,samples,glb_sha256:finalHash});
 }
 if(report.errors.length)throw Error(report.errors.join('\n'));report.status='PASS';report.browser=browser.version();
}catch(error){report.errors.push(error.stack);throw error;}finally{await writeFile(out+(gripOnly?'/grip-preview.json':previewOnly?'/quick-peek-check.json':'/preview.json'),JSON.stringify(report,null,2));await browser?.close();server.kill();}
