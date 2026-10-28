#!/usr/bin/env python3
"""Independent literal Information extraction plus frozen mixed-output controls."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
parser.add_argument('--before',type=Path,default=ROOT/'evidence/mixed-information-20261028/BEFORE-RESPONSES.json');args=parser.parse_args()
assert not args.evidence.exists();work=args.evidence.with_name(args.evidence.stem+'-cases');work.mkdir()
before=json.loads(args.before.read_text(encoding='utf-8-sig'));wanted=before['information']
source=ROOT/'examples/mixed-information.ts';options=json.loads((ROOT/'examples/mixed-information-options.json').read_text())
begin='[Begin Information]\n';end='[End Information]\n'
bridge_script="import fs from 'node:fs';import {run} from './_build/js/release/build/cmd/bridge/bridge.js';process.stdout.write(run(fs.readFileSync(process.argv[1],'ascii'),process.argv[2],'','')+'\\n');"
commands=[];checks=[];artifacts=[];failure=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,text):
 p=work/name;p.write_text(text,encoding='ascii',newline='');artifacts.append(p);return p
def information(text):
 assert text.count(begin)==text.count(end)==1
 return text.split(begin,1)[1].split(end,1)[0].splitlines()
def without_information(text):
 first=text.index(begin);last=text.index(end)+len(end);return text[:first]+text[last:]
def run(argv,code,label,kind):
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
 log=save(label+'.stdout.txt',r.stdout)
 commands.append({'label':label,'kind':kind,'argv':argv,'exitCode':r.returncode,'expectedExitCode':code,'stderr':r.stderr,'stdout':str(log)})
 assert r.returncode==code,(label,r.returncode,r.stderr)
 if code==2:assert not r.stdout
 else:assert not r.stderr
 return r
def bridge(file,label):
 return json.loads(run(['node','--input-type=module','-e',bridge_script,str(file),json.dumps({'command':'mixed',**options})],0,label,'compiled-bridge').stdout)
def cli(command,file,query,label,code=0,output=None):
 argv=['node',str(ROOT/'tools/touchstone.mjs'),command,str(file),json.dumps(query)]+([str(output)] if output else [])
 r=run(argv,code,label,'file-CLI')
 if output and code!=2:assert not r.stdout and output.exists();artifacts.append(output)
 return r
try:
 original=source.read_text(encoding='ascii');assert information(original)==wanted
 fixed=bridge(source,'fixed-information-response')
 assert information(fixed['text'])==wanted
 assert fixed['network']==before['withInformation']['network'] and fixed['order']==before['withInformation']['order']
 assert without_information(fixed['text'])==before['withInformation']['text']
 checks.append({'label':'literal-information-preserved-only-text-block-changes','lines':len(wanted),'networkAndOrderExactBeforeMatch':True})
 empty=save('no-information.ts',without_information(original))
 no_info=bridge(empty,'no-information-control');assert no_info==before['withoutInformation']
 checks.append({'label':'no-information-full-response-byte-compatible','entireParsedPayloadAndTextEqual':True})
 mixed_file=work/'mixed output.ts';cli('mixed',source,options,'actual-file-example',output=mixed_file)
 assert mixed_file.read_text(encoding='ascii')==fixed['text'] and information(mixed_file.read_text(encoding='ascii'))==wanted
 inspected=json.loads(cli('inspect',mixed_file,{},'actual-file-readback').stdout)
 assert inspected['information']==wanted and inspected['mixed_mode_order']==['D1,2','C1,2','S3']
 assert inspected['ports']==3 and inspected['reference_ohms']==[50,50,75] and inspected['frequency_hz']==[1.2e9,1.8e9]
 checks.append({'label':'actual-CLI-file-literal-and-parser-readback','informationLines':len(wanted),'modeAndReferencePreserved':True})
 old_text=before['withInformation']['text'];assert begin not in old_text
 mixed_input=save('already-mixed-input.ts',old_text.replace('[Network Data]',begin+'\n'.join(wanted)+'\n'+end+'[Network Data]',1))
 again=bridge(mixed_input,'already-mixed-information')
 assert information(again['text'])==wanted and again['order']==fixed['order'] and again['network']['reference_ohms']==[100,25,75]
 checks.append({'label':'already-mixed-input-single-information-copy','informationLines':len(wanted)})
 reduced=work/'reduced output.ts';cli('terminate-file',mixed_file,{'terminations':[[2,.25,.1]]},'new-metadata-handoff',output=reduced)
 assert information(reduced.read_text(encoding='ascii'))==wanted
 reduction=json.loads(cli('inspect',reduced,{},'metadata-handoff-readback').stdout)
 assert reduction['information']==wanted and reduction['ports']==2 and reduction['reference_ohms']==[50,50] and reduction['mixed_mode_order']==[]
 assert reduction['frequency_hz']==[1.2e9,1.8e9]
 checks.append({'label':'new-input-mixed-to-terminate-file-information-retained','informationLines':len(wanted),'old16NumericalCollectionRerun':False})
 noisy=save('noisy.ts','[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 21_12\n[Number of Frequencies] 1\n[Number of Noise Frequencies] 1\n[Network Data]\n1200000000 .1 0 .2 0 .3 0 .1 0\n[Noise Data]\n1200000000 2 .25 0 5\n[End]\n')
 forbidden=work/'must-not-write-noisy.ts';r=cli('mixed',noisy,options,'noisy-rejection-preserved',code=2,output=forbidden)
 assert 'cannot encode two-port noise' in r.stderr and not forbidden.exists()
 checks.append({'label':'noisy-input-refusal-preserved','noOutputWritten':True})
except Exception as exc:failure=exc
finally:
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'actualNodeProcesses':len(commands),
  'compiledBridgeProcesses':sum(x['kind']=='compiled-bridge' for x in commands),'fileCLIProcesses':sum(x['kind']=='file-CLI' for x in commands),
  'consumerChecks':len(checks),'commands':commands,'checks':checks,'newNumericalComparisons':0,'oldCollectionsRerun':False,
  'artifacts':[{'path':str(p),'sha256':sha(p)} for p in artifacts if p.exists()],
  'sourceSHA256':{k:sha(ROOT/k) for k in ['cmd/bridge/main.mbt','tools/verify-terminate-file.py','tools/verify-mixed-information.py',
   'examples/mixed-information.ts','examples/mixed-information-options.json','mixed_mode.mbt','document.mbt','versioned.mbt']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['complete','failure','actualNodeProcesses','compiledBridgeProcesses','fileCLIProcesses','consumerChecks']}))
if failure:raise failure
