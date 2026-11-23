import {chromium} from 'playwright';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
const out=process.env.FMS_HEATSY_OUTPUT||'outputs/heatsy-bodyweight',query=process.env.FMS_HEATSY_QUERY||'',quick=process.argv.includes('--poses-only');
const timing=JSON.parse(await readFile(`${out}/retarget.json`,'utf8'));
const fps=timing.fps,frameCount=timing.source_frames-1,duration=timing.duration;
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
let browser;const report={status:'FAIL',errors:[],samples:[],screenshots:[]};
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(Error(`Server exited ${c}`)));});
 browser=await chromium.launch(process.env.FMS_HEATSY_GPU==='1'?{channel:'chromium',args:['--use-angle=d3d11']}:{});const page=await browser.newPage({viewport:{width:1240,height:1150}});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(`http://127.0.0.1:${port}/studio/heatsy-squat/?${query}`);await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);if(await page.evaluate(()=>window.heatsy.error))throw Error(await page.evaluate(()=>window.heatsy.error));
 await mkdir(`${out}/poses`,{recursive:true});
 const indices=JSON.parse(await readFile(`${out}/sample-indices.json`,'utf8'));
 for(const [name,phase] of [['standing',0],['descent',.25],['bottom',.5],['ascent',.75],['return',1]]){
   await page.evaluate(p=>window.heatsy.seek(p),phase);
   report.samples.push({name,...await page.evaluate(i=>window.heatsy.sample(i),indices)});
   for(const view of ['front','side','three']){await page.locator(`[data-view="${view}"]`).click();const path=`${out}/poses/${name}-${view}.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
   if(['descent','bottom','ascent'].includes(name)){await page.evaluate(()=>window.heatsy.normalMode(true));const path=`${out}/poses/${name}-normals.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);await page.evaluate(()=>window.heatsy.normalMode(false));}
 }
 for(const phase of [.123,.337,.611]){await page.evaluate(p=>window.heatsy.seek(p),phase);report.samples.push({name:`interpolated-${phase}`,...await page.evaluate(i=>window.heatsy.sample(i),indices)});}
 if(!quick){
   for(const [name,phase] of [['standing',0],['descent',.25],['bottom',.5],['ascent',.75]]){await page.evaluate(p=>{window.heatsy.seek(p);window.heatsy.select('58');window.heatsy.focus();},phase);const path=`${out}/poses/${name}-latissimus-detail.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
   for(const region of ['hips','knees']){await page.evaluate(r=>{window.heatsy.seek(.5);window.heatsy.select('none');window.heatsy.focus(r);},region);const path=`${out}/poses/bottom-${region}-detail.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
   await page.evaluate(()=>window.heatsy.view('three'));
   const selections=[];
   for(const phase of [.25,.5,.75])for(const option of await page.evaluate(()=>window.heatsy.options)){
     await page.evaluate(({phase,value})=>{window.heatsy.seek(phase);window.heatsy.select(value);},{phase,value:option.value});
     const checks=await page.evaluate(()=>window.heatsy.inspect());
     if(checks[1].badColors)throw Error('Unexpected selection colors');
     if(Object.keys(checks[1].selected).map(Number).sort((a,b)=>a-b).join()!==[...option.codes].sort((a,b)=>a-b).join())throw Error('Selection mismatch');
     selections.push({phase,value:option.value,selected:checks[1].selected});
   }
   report.selection_checks=selections;
   for(const group of ['quads-L','quads-R','glutes-L','glutes-R']){await page.evaluate(g=>{window.heatsy.seek(.5);window.heatsy.select(g);window.heatsy.view(g.startsWith('quads')?'front':'rear');},group);const path=`${out}/poses/bottom-${group}.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
   for(const code of ['97','98','99','100','117','118']){await page.evaluate(c=>{window.heatsy.seek(.5);window.heatsy.select(c);window.heatsy.view(Number(c)<110?'rear':'front');},code);const path=`${out}/poses/bottom-muscle-${code}.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
   report.performance=[];
   for(const small of [false,true]){
     await page.evaluate(s=>{window.heatsy.quickPeek(s);window.heatsy.select('quads-L');window.heatsy.view('three');},small);
     const measurements=await page.evaluate(async()=>{const times=[],intervals=[];let previous=performance.now();for(let i=0;i<120;i++){await new Promise(requestAnimationFrame);const start=performance.now();intervals.push(start-previous);previous=start;window.heatsy.seek(i/120);times.push(performance.now()-start);}times.sort((a,b)=>a-b);intervals.sort((a,b)=>a-b);return {median_animation_frame_interval_ms:intervals[60],p95_animation_frame_interval_ms:intervals[114],median_cpu_seek_and_submit_ms:times[60],p95_cpu_seek_and_submit_ms:times[114],render:window.heatsy.performance(),userAgent:navigator.userAgent};});
     report.performance.push({mode:small?'quick-peek':'detailed',...measurements});
     if(small){for(const [name,phase] of [['standing',0],['descent',.25],['bottom',.5],['ascent',.75]]){await page.evaluate(p=>window.heatsy.seek(p),phase);const path=`${out}/poses/${name}-quick-peek.png`;await page.locator('.comparison').screenshot({path});report.screenshots.push(path);}}
   }
   await page.evaluate(()=>window.heatsy.quickPeek(false));
   await page.evaluate(()=>{window.heatsy.select('none');window.heatsy.view('three');window.heatsy.seek(.5);});
   // Exercise actual controls, including endpoint wrap and matched orbit.
   await page.locator('#scrub').fill('250');await page.locator('#scrub').dispatchEvent('input');
   const times=await page.evaluate(()=>window.heatsy.times()),durations=await page.evaluate(()=>window.heatsy.durations),starts=await page.evaluate(()=>window.heatsy.starts);
   if(times.some((t,i)=>Math.abs(t-starts[i]-durations[i]*.25)>1e-6))throw Error('Scrub not synchronized');
   await page.locator('#play').click();await page.waitForTimeout((duration+.3)*1000);report.playback=await page.evaluate(()=>({times:window.heatsy.times(),durations:window.heatsy.durations,starts:window.heatsy.starts}));await page.evaluate(()=>window.heatsy.pause());
   const phases=report.playback.times.map((t,i)=>(t-report.playback.starts[i])/report.playback.durations[i]);if(phases[0]<=0||Math.abs(phases[0]-phases[1])>1e-6)throw Error('Playback not synchronized');
   const paused=await page.evaluate(()=>window.heatsy.times());await page.waitForTimeout(150);if(JSON.stringify(paused)!==JSON.stringify(await page.evaluate(()=>window.heatsy.times())))throw Error('Pause failed');
   report.speed_checks=[];
   for(const speed of ['0.5','2']){await page.locator('#speed').selectOption(speed);const check=await page.evaluate(async s=>{window.heatsy.seek(0);document.querySelector('#play').click();const begin=performance.now();await new Promise(r=>setTimeout(r,750));const elapsed=(window.heatsy.lastPlaybackTick-window.heatsy.playStartedAt)/1000;const wallElapsed=(performance.now()-begin)/1000;const played=window.heatsy.times()[1];window.heatsy.pause();return {speed:Number(s),elapsed,wallElapsed,played};},speed);report.speed_checks.push(check);if(Math.abs(check.played-(check.elapsed*check.speed)%duration)>.02)throw Error(`Speed mismatch: ${JSON.stringify(check)}`);}
   const before=await page.evaluate(()=>window.heatsy.inspect().map(p=>p.camera));const box=await page.locator('#roundtrip canvas').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+85,box.y+box.height/2+20,{steps:8});await page.mouse.up();const after=await page.evaluate(()=>window.heatsy.inspect().map(p=>p.camera));if(JSON.stringify(before)===JSON.stringify(after)||after[0].some((v,i)=>Math.abs(v-after[1][i])>1e-10))throw Error('Orbit mismatch');report.orbit={before,after};
   await page.goto(`http://127.0.0.1:${port}/studio/heatsy-squat/?capture&${query}`);await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);
   for(const view of ['front','side']){
     await mkdir(`${out}/frames-${view}`,{recursive:true});await page.evaluate(v=>window.heatsy.view(v),view);
     for(let frame=0;frame<frameCount;frame++){await page.evaluate(p=>window.heatsy.seek(p),frame/frameCount);const data=await page.evaluate(()=>window.heatsy.canvas());await writeFile(`${out}/frames-${view}/${String(frame).padStart(4,'0')}.png`,Buffer.from(data.split(',')[1],'base64'));}
   }
   await page.evaluate(()=>{window.heatsy.view('three');window.heatsy.seek(.5);});const data=await page.evaluate(()=>window.heatsy.canvas());await writeFile(`${out}/poster.png`,Buffer.from(data.split(',')[1],'base64'));
 }
 report.glb_sha256=createHash('sha256').update(await readFile(`${out}/heatsy-squat.glb`)).digest('hex');report.browser=browser.version();report.fps=fps;report.frame_count=frameCount;report.duration=duration;
 if(report.errors.length)throw Error(report.errors.join('\n'));report.status='PASS';
}catch(e){report.errors.push(e.stack);throw e;}finally{await writeFile(`${out}/${quick?'poses-preview':'viewer'}.json`,JSON.stringify(report,null,2));await browser?.close();server.kill();}
console.log('PASS: Heatsy squat viewer checks and captures');
