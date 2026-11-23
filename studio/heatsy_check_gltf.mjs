import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import validator from 'gltf-validator';
const out='outputs/heatsy-probe/compatibility';
for(const [name,path] of [['source','work/heatsy/model/body_superficial.app5m.glb'],['roundtrip',`${out}/roundtrip.glb`],['mpfb',`${out}/mpfb-regression/squat-technical.glb`]]){
 const bytes=await readFile(path),report=await validator.validateBytes(new Uint8Array(bytes),{uri:path,maxIssues:0});
 report.sha256=createHash('sha256').update(bytes).digest('hex');
 const warnings=report.issues.messages.filter(m=>m.severity===1);
 const allowed=new Set(['NODE_SKINNED_MESH_NON_ROOT',...(name==='source'?['ACCESSOR_JOINTS_USED_ZERO_WEIGHT']:[])]);
 report.status=report.issues.numErrors===0&&!report.issues.truncated&&warnings.every(m=>allowed.has(m.code))?'PASS':'FAIL';
 report.warning_dispositions={NODE_SKINNED_MESH_NON_ROOT:'Retained from source: no runtime parent transforms; static browser skinning is independently compared. No other consumer or animation claim.',ACCESSOR_JOINTS_USED_ZERO_WEIGHT:'Source-only unused joint slots have nonzero indices and exactly zero weights. They contribute zero; compare checks all nonzero joint-name/weight contributions. Blender resets unused slots without changing effective skinning.'};
 report.issue_counts=Object.fromEntries([...new Set(report.issues.messages.map(m=>m.code))].map(code=>[code,report.issues.messages.filter(m=>m.code===code).length]));
 await writeFile(`${out}/${name}-gltf.json`,JSON.stringify(report,null,2));
 console.log(`${name}: ${report.status}, ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
 if(report.status!=='PASS')throw Error(`${name} validation failed`);
}
