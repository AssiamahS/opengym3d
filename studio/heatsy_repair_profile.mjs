import {chromium} from 'playwright';
import {writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
const out='outputs/heatsy-repair';
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
const report={method:'Warmup 8 frames, 48 requestAnimationFrame intervals with real seek/render; median/p95 wall intervals and CPU submission. No screenshot or readback in timed interval. Both mixers updated even in single-visible-model control.',runs:[]};
report.glb_sha256=createHash('sha256').update(await readFile(out+'/heatsy-squat.glb')).digest('hex');
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);});
 for(const config of [{name:'default-headless-shell',options:{}},{name:'chromium-d3d11-headless',options:{channel:'chromium',args:['--use-angle=d3d11']}}]){
  const browser=await chromium.launch(config.options);
  try{
   const page=await browser.newPage({viewport:{width:1240,height:1150}});
   for(const test of [
    {name:'dual-detailed',options:{}},{name:'single-detailed',options:{single:true}},
    {name:'single-320',small:true,options:{single:true}},
    {name:'single-unlit',options:{single:true,unlit:true}},
    {name:'single-rigid-shader',options:{single:true,skinning:false}},
    {name:'empty-scenes',options:{empty:true}},
    {name:'dual-no-preserved-buffer',noPreserve:true,options:{}}]){
    await page.goto(`http://127.0.0.1:${port}/studio/heatsy-squat/?repair=final${test.noPreserve?'&no-preserve=1':''}`);
    await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);
    if(await page.evaluate(()=>window.heatsy.error))throw Error(await page.evaluate(()=>window.heatsy.error));
    await page.evaluate(s=>window.heatsy.quickPeek(!!s),test.small);
    const gpu=await page.evaluate(o=>window.heatsy.profile(o),test.options);
    const measurements=await page.evaluate(async()=>{
     const intervals=[],cpu=[];let previous;
     for(let i=0;i<56;i++){await new Promise(requestAnimationFrame);const start=performance.now();if(i>=8)intervals.push(start-previous);previous=start;window.heatsy.seek((i%48)/48);if(i>=8)cpu.push(performance.now()-start);}
     intervals.sort((a,b)=>a-b);cpu.sort((a,b)=>a-b);
     return {samples:48,median_frame_ms:intervals[24],p95_frame_ms:intervals[45],median_cpu_submit_ms:cpu[24],p95_cpu_submit_ms:cpu[45],render:window.heatsy.performance()};
    });
    const highlight=await page.evaluate(()=>{const values=[];for(let i=0;i<20;i++){const start=performance.now();window.heatsy.select(i%2?'quads-L':'none');values.push(performance.now()-start);}values.sort((a,b)=>a-b);return {median_update_and_submit_ms:values[10],maximum_ms:values[19],updates:20};});
    const run={configuration:config.name,launchOptions:config.options,browser:browser.version(),case:test.name,gpu,measurements,highlight};report.runs.push(run);
    console.log(config.name,test.name,measurements.median_frame_ms,gpu[1].unmaskedRenderer);
   }
  }finally{await browser.close();}
 }
 report.status='PASS';
}finally{await writeFile(out+'/performance-profile.json',JSON.stringify(report,null,2));server.kill();}
