// Capture the actual exported GLB via the same local viewer; no second animation.
import {chromium} from 'playwright';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
const out='outputs/bodyweight';
const server=spawn('python',['-m','http.server','0','--bind','127.0.0.1'],{env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
let browser;
try {
 const port=await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{const m=d.toString().match(/port (\d+)/);if(m)resolve(m[1]);});server.on('error',reject);server.on('exit',c=>reject(new Error(`server exited ${c}`)));});
 browser=await chromium.launch();
 const page=await browser.newPage({viewport:{width:512,height:512}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://127.0.0.1:${port}/studio/?capture`);
 await page.waitForFunction(()=>window.fms?.ready||window.fms?.error);
 const duration=await page.evaluate(()=>window.fms.duration);
 if(!duration)throw new Error('No exported animation');
 const fps=30,count=Math.round(duration*fps),samples={},floor=[];
 for(const view of ['front','side','three']) {
   const dir=`work/frames-${view}`;await mkdir(dir,{recursive:true});
   await page.evaluate(v=>window.fms.view(v),view);
   for(let i=0;i<count;i++) {
     await page.evaluate(t=>window.fms.seek(t),i/fps);
     await page.screenshot({path:`${dir}/${String(i).padStart(4,'0')}.png`});
     if(view==='front')floor.push(await page.evaluate(()=>window.fms.floor()));
     if(view==='front'&&i%15===0)samples[i]=await page.evaluate(()=>window.fms.positions());
   }
   await page.evaluate(()=>window.fms.seek(1.5));
   await page.screenshot({path:`${out}/${view}-bottom.png`});
 }
 await page.screenshot({path:`${out}/squat-technical.png`});
 await page.evaluate(()=>{window.fms.view('front');window.fms.seek(.75);});
 const times=await page.evaluate(()=>window.fms.trackTimes());
 if(times.some(t=>Math.abs(t-.75)>1e-5))errors.push('Clip seeking not synchronized');
 // Exercise real playback through > one complete loop in each required view.
 await page.evaluate(()=>document.body.classList.remove('capture'));
 const playback=[];
 for(const view of ['front','side']){
   await page.evaluate(v=>{window.fms.pause();window.fms.view(v);window.fms.seek(0);},view);
   await page.locator('#play').click();
   await delay((duration+.5)*1000);
   const times=await page.evaluate(()=>window.fms.trackTimes());
   playback.push({view,times});
   if(times.every(t=>t===0))errors.push(`Playback did not advance: ${view}`);
 }
 const hash=createHash('sha256').update(await readFile(`${out}/squat-technical.glb`)).digest('hex');
 await writeFile(`${out}/preview.json`,JSON.stringify({status:errors.length?'FAIL':'PASS',glb_sha256:hash,duration,fps,frame_count:count,views:['front','side','three'],capture:'Three.js final GLB, exact i/fps timestamps, endpoint omitted for loop',browser:browser.version(),errors,playback,minimum_mesh_y:Math.min(...floor),mesh_floor_by_frame:floor,synchronized_seek_times:times,sampled_bones:samples},null,2));
 if(errors.length)throw new Error(errors.join('\n'));
 console.log(`Captured ${count} frames per view, ${duration}s; ${hash}`);
} finally {await browser?.close();server.kill();}
