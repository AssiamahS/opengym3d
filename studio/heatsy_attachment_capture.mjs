// Matched detail evidence through the existing viewer, without changing materials.
import {chromium} from 'playwright';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
const out='outputs/heatsy-attachment';
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
let browser;
try {
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(Error(`Server exit ${c}`)));});
 browser=await chromium.launch({channel:'chromium',args:['--use-angle=d3d11']});
 const page=await browser.newPage({viewport:{width:1240,height:1150}}),errors=[],screenshots=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://127.0.0.1:${port}/studio/heatsy-squat/?repair=attachment-05&compare=before`);
 await page.waitForFunction(()=>window.heatsy?.ready||window.heatsy?.error);
 if(await page.evaluate(()=>window.heatsy.error))throw Error(await page.evaluate(()=>window.heatsy.error));
 await mkdir(out+'/details',{recursive:true});
 for(const [pose,phase] of [['standing',0],['descent',.25],['bottom',.5]]) {
  await page.evaluate(p=>{window.heatsy.seek(p);window.heatsy.select('none');},phase);
  for(const region of ['shoulder','hips','knees']) {
   await page.evaluate(r=>window.heatsy.focus(r),region);
   const path=`${out}/details/${pose}-${region}.png`;await page.screenshot({path});screenshots.push(path);
  }
  await page.evaluate(()=>window.heatsy.view('rear'));
  const path=`${out}/details/${pose}-back.png`;await page.screenshot({path});screenshots.push(path);
 }
 const poses=JSON.parse(await readFile(out+'/diagnostic-poses.json','utf8'));
 const heat=JSON.parse(await readFile(out+'/strain-heat.json','utf8'));
 for(const name of Object.keys(poses.poses)) {
  await page.evaluate(({poses,name,heat})=>{window.heatsy.pose(poses,name);window.heatsy.view('three');window.heatsy.heat(heat);},{poses,name,heat:heat[name]});
  const path=`${out}/details/control-${name}-strain.png`;await page.screenshot({path});screenshots.push(path);
 }
 await page.evaluate(()=>{window.heatsy.select('none');window.heatsy.seek(.5);window.heatsy.view('three');window.heatsy.axes(true);});
 await page.screenshot({path:out+'/details/bottom-joint-axes.png'});
 screenshots.push(out+'/details/bottom-joint-axes.png');
 if(errors.length)throw Error(errors.join('\n'));
 await writeFile(out+'/details.json',JSON.stringify({status:'PASS',errors,screenshots},null,2));
} finally {await browser?.close();server.kill();}
