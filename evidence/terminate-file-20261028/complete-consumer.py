import ast,hashlib,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]/'projects/moonbit-touchstone'
WORK=OUT/'remaining-first-cases';WORK.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
prefix=read(OUT/'independent-final.json');base=read(OUT/'BASELINE.json')
assert not prefix['complete'] and prefix['actualCLIProcesses']==25 and prefix['independentGTPointComparisons']==6
assert prefix['commands'][-1]['label']=='noise-not-silently-discarded'
assert 'Two-Port Data Order' in prefix['commands'][-1]['stderr']
old_tool=OUT/'verify-terminate-file-prefix-executed.py';current_tool=ROOT/'tools/verify-terminate-file.py'
assert sha(old_tool)==prefix['sourceSHA256']['tools/verify-terminate-file.py']
old=old_tool.read_text(encoding='utf-8');new=current_tool.read_text(encoding='utf-8')
old_marker=r'[Number of Ports] 2\n[Number of Frequencies] 1\n[Number of Noise Frequencies] 1'
new_marker=r'[Number of Ports] 2\n[Two-Port Data Order] 21_12\n[Number of Frequencies] 1\n[Number of Noise Frequencies] 1'
assert old.count(old_marker)==1 and new==old.replace(old_marker,new_marker,1)
for k,v in prefix['sourceSHA256'].items():
 if k!='tools/verify-terminate-file.py':assert sha(ROOT/k)==v,k
commands=list(prefix['commands'][:-1]);checks=list(prefix['checks']);artifacts=list(prefix['artifacts'])
assert len(commands)==24 and all(x['exitCode']==x['expectedExitCode'] for x in commands)
for item in artifacts:assert sha(Path(item['path']))==item['sha256'],item
tail=[]
def call(command,source,options,code,label,output=None):
 argv=['node',str(ROOT/'tools/touchstone.mjs'),command,str(source),json.dumps(options)]+([str(output)] if output else [])
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
 log=WORK/(label+'.stdout.txt');log.write_text(r.stdout,encoding='utf-8');artifacts.append({'path':str(log),'sha256':sha(log)})
 item={'label':label,'argv':argv,'exitCode':r.returncode,'expectedExitCode':code,'stderr':r.stderr,'stdout':str(log)}
 tail.append(item);assert r.returncode==code,(label,r.stderr)
 if code==2:assert not r.stdout and not output.exists()
 else:assert not r.stderr
 return r
tree=ast.parse(new);literal=None
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='save' and len(node.args)==2 and isinstance(node.args[0],ast.Constant) and node.args[0].value=='noise.ts':literal=ast.literal_eval(node.args[1])
assert literal and '[Two-Port Data Order] 21_12' in literal
noise=WORK/'noise.ts';noise.write_text(literal,encoding='ascii',newline='');artifacts.append({'path':str(noise),'sha256':sha(noise)})
r=call('terminate-file',noise,{'terminations':[[1,0,0]]},2,'noise-not-silently-discarded',WORK/'must-not-drop-noise.ts')
assert 'cannot preserve noise' in r.stderr
checks.append({'label':'noise-not-silently-discarded','rejectedWithoutOutput':True,'validTwoPortOrder':True})
singular=WORK/'singular.s2p';singular.write_text('# Hz S RI R 50\n1 0 0 0 0 0 0 1 0\n',encoding='ascii',newline='')
artifacts.append({'path':str(singular),'sha256':sha(singular)})
call('terminate-file',singular,{'terminations':[[1,1,0]]},2,'singular-feedback',WORK/'must-not-write-singular.ts')
checks.append({'label':'singular-feedback','rejectedWithoutOutput':True})
r=call('terminate',ROOT/'examples/loaded-four-port.ts',base['options'],0,'legacy-terminate-JSON-preserved')
value=json.loads(r.stdout);assert value==base['oldReducedNetwork'] and 'text' not in value
checks.append({'label':'legacy-terminate-JSON-preserved','equalToPreImplementationBaseline':True})
commands+=tail;assert len(commands)==27 and len(checks)==19
result={**prefix,'complete':True,'failure':None,'actualCLIProcesses':27,'consumerChecks':19,'commands':commands,'checks':checks,'artifacts':artifacts,
 'sourceSHA256':{k:sha(ROOT/k) for k in prefix['sourceSHA256']},
 'verificationAssembly':{'acceptedPrefixCLIProcesses':24,'acceptedPrefixEvidence':'independent-final.json','newTailCLIProcesses':3,
  'tailScript':'complete-consumer.py','noAcceptedPrefixReexecuted':True,'prefixExecutedValidatorSHA256':sha(old_tool),
  'finalValidatorSHA256':sha(current_tool),'onlyRemainingValidatorChange':'One noisy fixture literal adds mandatory Two-Port Data Order; exact source replacement proven'},
 'developmentFailures':['independent-first.json: mixed fixture wrongly assumed information propagated by existing mixed command',
  'independent-final.json: noisy fixture missing mandatory Two-Port Data Order; parser rejected before new noise guard']}
(OUT/'independent-complete.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'complete':True,'acceptedConsumerCLIProcesses':27,'consumerChecks':19,'independentGTPointComparisons':6,'newTailCLIProcesses':3}))
