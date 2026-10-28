// Real file workflow: intentionally failing analysis, successfully reproduced.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
try {
  if (process.argv.length!==3) throw new Error('Usage: node examples/gain_receipt_demo.mjs NEW-OUTPUT-DIRECTORY');
  const output=path.resolve(process.argv[2]);
  fs.mkdirSync(output); // Fresh directory only, never overwrite prior evidence.
  const receipt=path.join(output,'gain-receipt.json');
  const sample=path.join(root,'examples/power-gain.s2p');
  const tool=path.join(root,'tools/touchstone.mjs');
  const record=spawnSync(process.execPath,[tool,'gain-record',sample,'@'+path.join(root,'examples/gain-check-ohms.json'),receipt],{cwd:root,encoding:'utf8',windowsHide:true});
  if (record.status!==3) throw new Error(record.stderr || 'expected a saved sampled-limit failure');
  const reviewed=spawnSync(process.execPath,[tool,'gain-review',sample,'@'+receipt],{cwd:root,encoding:'utf8',windowsHide:true});
  if (reviewed.status!==0) throw new Error(reviewed.stderr || 'receipt replay did not match');
  const result=JSON.parse(reviewed.stdout);
  if (result.status!=='reproduced' || result.recorded_status!=='fail' || result.current_status!=='fail') throw new Error('reproduced failure was not preserved');
  fs.writeFileSync(path.join(output,'gain-review.json'),reviewed.stdout,{encoding:'utf8',flag:'wx'});
  process.stdout.write(reviewed.stdout);
} catch(error) {
  console.error('gain receipt demo: '+error.message);
  process.exitCode=2;
}
