import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {run} from '../_build/js/release/build/cmd/bridge/bridge.js';

const scratch=fs.mkdtempSync(path.join(os.tmpdir(),'moon-touchstone-cli-'));
let checks=0;
function cli(args,success=true) {
  const p=spawnSync(process.execPath,['tools/touchstone.mjs',...args],{encoding:'utf8',timeout:15000});
  assert.equal(p.status,success?0:2,p.stderr); checks++; return p;
}
try {
  const source='examples/attenuator.s2p';
  assert.equal(JSON.parse(cli(['inspect',source]).stdout).ports,2);
  const delay=JSON.parse(cli(['delay',source,'{"input":0,"output":1}']).stdout);
  assert.ok(delay.every(x=>Math.abs(x-1e-9)<1e-20)); checks++;
  const out=path.join(scratch,'normalized.ts');
  cli(['normalize',source,'{}',out]);
  const before=fs.readFileSync(out);
  cli(['normalize',source,'{}',out],false);
  assert.deepEqual(fs.readFileSync(out),before); checks++;
  cli(['normalize',source,'{}',source],false);
  cli(['validate',out]);
  cli(['convert',source,'{"parameter":"UNKNOWN"}'],false);
  cli(['select',source,'{"selection":[0,0]}'],false);
  cli(['cascade',source,JSON.stringify({right_file:source})]);
  const abcd=JSON.parse(cli(['rf-convert',source,'{"parameter":"ABCD"}']).stdout);
  assert.equal(abcd.parameter,'ABCD');checks++;
  const mixed=path.join(scratch,'mixed.ts');
  cli(['mixed',source,'{"pairs":[[0,1]]}',mixed]);
  assert.deepEqual(JSON.parse(cli(['modal',mixed]).stdout).reference_ohms,[100,25]);checks++;
  assert.equal(JSON.parse(cli(['single',mixed]).stdout).ports,2);checks++;
  assert.equal(JSON.parse(cli(['modal-metrics',mixed,'{"output_pair":0,"input_pair":0}']).stdout).length,3);checks++;
  assert.equal(JSON.parse(cli(['terminate',source,'{"terminations":[[1,0.2,0.1]]}']).stdout).ports,1);checks++;
  assert.equal(JSON.parse(cli(['stability',source]).stdout).stability.length,3);checks++;
  const noisy=path.join(scratch,'noisy.ts');
  fs.writeFileSync(noisy,'[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 1\n[Two-Port Data Order] 12_21\n[Number of Noise Frequencies] 1\n[Network Data]\n1 .1 0 .02 0 2 0 .2 0\n[Noise Data]\n1 1.5 .2 30 10\n[End]\n');
  assert.equal(JSON.parse(cli(['noise',noisy,'{"source":[0.2,0.1],"figure_db":3}']).stdout).figure_db.length,1);checks++;
  cli(['mixed',noisy,'{"pairs":[[0,1]]}'],false);
  cli(['select',noisy,'{"selection":[1,0]}'],false);
  const cascaded=path.join(scratch,'noisy-cascade.ts');
  cli(['cascade',noisy,JSON.stringify({right_file:noisy}),cascaded]);
  assert.equal(JSON.parse(cli(['inspect',cascaded]).stdout).noise.length,1);checks++;
  const binary=path.join(scratch,'nul.s2p');
  fs.writeFileSync(binary,'# Hz S RI R 50\n1 0 0 0 0 0 0 0 0\x00');
  cli(['validate',binary],false);
  fs.writeFileSync(binary,Buffer.from([0xff]));
  cli(['validate',binary],false);
  assert.throws(()=>run(fs.readFileSync(source,'ascii'),'{"command":"metrics","ports":2,"input":-1,"output":1}','',''));
  checks++;
  console.log(JSON.stringify({checks,status:'passed'}));
} finally {
  // Only this uniquely created test directory, never a supplied output path.
  fs.rmSync(scratch,{recursive:true,force:true});
}
