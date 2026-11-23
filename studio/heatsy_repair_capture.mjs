import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawn} from 'node:child_process';
const out='outputs/heatsy-repair';
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
let browser;
try{
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);});
 browser=await chromium.launch({channel:'chromium',args:['--use-angle=d3d11']});
 const page=await browser.newPage({viewport:{width:1240,height:1150}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await mkdir(out+'/experiments',{recursive:true});
 const poses=JSON.parse(await readFile(out+'/diagnostic-poses.json','utf8')),heat=JSON.parse(await readFile(out+(process.argv.includes('--final')?'/accepted-strain-heat.json':'/strain-heat.json'),'utf8'));
 const report={screenshots:[],errors,browser:browser.version()};
 for(const variant of (process.argv.includes('--final')?['final']:process.argv.includes('--guarded')?['guarded-25','guarded-35']:process.argv.includes('--coherent')?['coherent-25','coherent-35']:['spatial-20','spatial-30'])){
  await page.goto(`http://127.0.0.1:${port}/studio/heatsy-squat/?repair=${variant}&compare=before`);
  await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);if(await page.evaluate(()=>window.heatsy.error))throw Error(await page.evaluate(()=>window.heatsy.error));
  report.renderer=await page.evaluate(()=>window.heatsy.profile());
  for(const [name,phase] of [['standing',0],['descent',.25],['bottom',.5]]){
   await page.evaluate(p=>window.heatsy.seek(p),phase);
   for(const region of ['shoulder','hips','knees']){await page.evaluate(r=>window.heatsy.focus(r),region);const path=`${out}/experiments/${variant}-${name}-${region}.png`;await page.screenshot({path});report.screenshots.push(path);}
  }
  if(variant==='spatial-20'||variant==='final')for(const name of Object.keys(poses.poses)){
   await page.evaluate(({poses,name,heat})=>{window.heatsy.pose(poses,name);window.heatsy.view('three');window.heatsy.heat(heat);},{poses,name,heat:heat[name]});
   const path=`${out}/experiments/control-${variant}-${name}-strain.png`;await page.screenshot({path});report.screenshots.push(path);
  }
  await page.evaluate(()=>{window.heatsy.select('none');window.heatsy.seek(.5);window.heatsy.view('three');window.heatsy.axes(true);});
  await page.screenshot({path:`${out}/experiments/${variant}-axes.png`});await page.evaluate(()=>window.heatsy.axes(false));
 }
 if(errors.length)throw Error(errors.join('\n'));
 await writeFile(out+`/experiment-viewer-${process.argv.at(-1).replaceAll('-','')}.json`,JSON.stringify(report,null,2));
 console.log('PASS experimental captures',report.screenshots.length,report.renderer);
}finally{await browser?.close();server.kill();}
