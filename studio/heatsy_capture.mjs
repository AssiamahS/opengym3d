import {chromium} from 'playwright';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
const out='outputs/heatsy-probe/compatibility';
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
let browser;
const report={status:'FAIL',errors:[],screenshots:[],selection_checks:[]};
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(Error(`server exited ${c}`)));});
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1240,height:1050}});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(`http://127.0.0.1:${port}/studio/heatsy/`);await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);if(await page.evaluate(()=>window.heatsy.error))throw Error(await page.evaluate(()=>window.heatsy.error));
 await mkdir(`${out}/screenshots`,{recursive:true});
 for(const view of ['front','side','three','rear']){await page.locator(`[data-view="${view}"]`).click();const path=`${out}/screenshots/neutral-${view}.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);}
 const entries=await page.evaluate(()=>window.heatsy.entries),options=await page.evaluate(()=>window.heatsy.options);
 for(const option of options.filter(o=>o.value!=='none')){
   await page.selectOption('#selection',option.value);
   const related=entries.filter(e=>option.codes.includes(e.code));const right=related[0].side==='R';const view=related[0].group==='quads'?'front':related.length>1?'rear':related[0].part==='tensor_fasciae_latae'?(right?'sideRight':'side'):(right?'rearThreeRight':'rearThree');await page.evaluate(v=>window.heatsy.view(v),view);
   const checks=await page.evaluate(()=>window.heatsy.inspect());
   for(const [i,check] of checks.entries()){
     if(check.badColors)throw Error(`Unexpected highlighted region: ${option.value}`);
     if(Object.keys(check.selected).map(Number).sort((a,b)=>a-b).join()!==[...option.codes].sort((a,b)=>a-b).join())throw Error('Selection ID mismatch');
     for(const e of related){const bounds=check.bounds[e.code];if(!bounds)throw Error('Missing selected geometry');if(e.side==='L'&&bounds[0][0]<-1e-4)throw Error('Left selection crosses to right');if(e.side==='R'&&bounds[1][0]>1e-4)throw Error('Right selection crosses to left');if(i===0&&check.selected[e.code]!==e.vertices)throw Error('Source vocabulary vertex count mismatch');}
   }
   if(JSON.stringify(checks[0].camera)!==JSON.stringify(checks[1].camera))throw Error('Cameras not matched');
   const path=`${out}/screenshots/select-${option.value}-${view}.png`;await page.screenshot({path,fullPage:true});report.screenshots.push(path);report.selection_checks.push({option,checks});
 }
 await page.selectOption('#selection','none');await page.locator('[data-view="three"]').click();
 const before=await page.evaluate(()=>window.heatsy.inspect().map(p=>p.camera));const box=await page.locator('#original canvas').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+90,box.y+box.height/2+30,{steps:8});await page.mouse.up();const after=await page.evaluate(()=>window.heatsy.inspect().map(p=>p.camera));report.orbit={before,after};if(JSON.stringify(before)===JSON.stringify(after)||after[0].some((v,i)=>Math.abs(v-after[1][i])>1e-10))throw Error('Synchronized orbit failed');
 report.metrics=await page.evaluate(()=>window.heatsy.metrics);report.browser=browser.version();
 await writeFile(`${out}/browser-positions.json`,JSON.stringify(await page.evaluate(()=>window.heatsy.samplePositions())));
 // Check baseline viewer operational without writing any canonical output.
 await page.goto(`http://127.0.0.1:${port}/studio/`);await page.waitForFunction(()=>window.fms?.ready||window.fms?.error);if(await page.evaluate(()=>window.fms.error))throw Error('Baseline viewer failed');await page.evaluate(()=>{window.fms.pause();window.fms.seek(.75);});report.bodyweight_viewer=await page.evaluate(()=>({duration:window.fms.duration,times:window.fms.trackTimes()}));if(report.bodyweight_viewer.times.some(t=>Math.abs(t-.75)>1e-5))throw Error('Baseline scrub failed');
 report.hashes={};for(const file of ['roundtrip.glb','validation.json'])report.hashes[file]=createHash('sha256').update(await readFile(`${out}/${file}`)).digest('hex');
 if(report.errors.length)throw Error(report.errors.join('\n'));report.status='PASS';
}catch(e){report.errors.push(e.stack);throw e;}finally{await writeFile(`${out}/viewer.json`,JSON.stringify(report,null,2));await browser?.close();server.kill();}
console.log(`PASS: ${report.screenshots.length} screenshots, ${report.selection_checks.length} selections, synchronized orbit and baseline scrub`);
