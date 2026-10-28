// File-only host: load original ports 1/2, retain 0/3 as reduced 0/1, then GT.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
try {
  if(process.argv.length!==3) throw new Error('Usage: node examples/terminate_file_demo.mjs NEW-OUTPUT-DIRECTORY');
  const out=path.resolve(process.argv[2]);fs.mkdirSync(out);
  const tool=path.join(root,'tools/touchstone.mjs');
  const reduced=path.join(out,'loaded-two-port.ts');
  const receipt=path.join(out,'gain-receipt.json');
  const terminate=spawnSync(process.execPath,[tool,'terminate-file',path.join(root,'examples/loaded-four-port.ts'),'@'+path.join(root,'examples/terminate-four-port.json'),reduced],{cwd:root,encoding:'utf8',windowsHide:true});
  if(terminate.status!==0) throw new Error(terminate.stderr || 'file termination failed');
  const gain=spawnSync(process.execPath,[tool,'gain-record',reduced,'@'+path.join(root,'examples/terminated-gain-check.json'),receipt],{cwd:root,encoding:'utf8',windowsHide:true});
  if(gain.status!==3) throw new Error(gain.stderr || 'expected a saved sampled-limit failure');
  const result=JSON.parse(fs.readFileSync(receipt,'utf8'));
  if(result.result.status!=='fail') throw new Error('analysis failure was lost');
  process.stdout.write(JSON.stringify({reduced,receipt,status:result.result.status},null,2)+'\n');
} catch(error) {
  console.error('terminate file demo: '+error.message);process.exitCode=2;
}
