import {chromium} from 'playwright';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch();
try {
 const page=await browser.newPage({viewport:{width:1100,height:900}}), errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/studio/');
 await page.waitForFunction(()=>window.fms?.ready);
 await page.evaluate(()=>{window.fms.pause();window.fms.seek(1.5);});
 await page.getByRole('button',{name:'Side',exact:true}).click();
 await page.screenshot({path:'outputs/bodyweight/viewer-side.png',fullPage:true});
 await page.getByRole('button',{name:'Three-quarter',exact:true}).click();
 await page.screenshot({path:'outputs/bodyweight/viewer.png',fullPage:true});
 const video=await page.evaluate(async()=>{const v=document.querySelector('video');v.muted=true;await v.play();return {duration:v.duration,width:v.videoWidth,height:v.videoHeight,loop:v.loop};});
 await page.waitForTimeout((video.duration+.5)*1000);
 const videoTime=await page.evaluate(()=>document.querySelector('video').currentTime);
 if(!(videoTime>0 && videoTime<1.5))errors.push('MP4 loop did not wrap');
 await page.locator('#scrub').fill('750');
 await page.locator('#scrub').dispatchEvent('input');
 const times=await page.evaluate(()=>window.fms.trackTimes());
 const duration=await page.evaluate(()=>window.fms.duration);
 if(times.some(t=>Math.abs(t-duration*.75)>1e-5))errors.push('UI scrub failed');
 await writeFile('outputs/bodyweight/viewer-smoke.json',JSON.stringify({status:errors.length?'FAIL':'PASS',errors,video,videoTimeAfterLoop:videoTime,scrubTimes:times,browser:browser.version()},null,2));
 if(errors.length)throw new Error(errors.join('\n'));
 console.log('Viewer loads, preset cameras work, UI scrub works, MP4 decodes and loops.');
} finally {await browser.close();}
