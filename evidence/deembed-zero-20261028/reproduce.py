import hashlib,json,os,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]/'projects/moonbit-touchstone'
assert not (OUT/'BASELINE.json').exists()
temp=OUT/'runtime-temp';temp.mkdir(exist_ok=False)
env=dict(os.environ,NODE_DISABLE_COMPILE_CACHE='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
bridge=ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(bridge)==json.loads((OUT/'COMPILED-BEFORE.json').read_text())['sha256']
def fixture(matrix):
 return '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 1\n[Begin Information]\nKnown fixture identity control\n[End Information]\n[Network Data]\n1000000000 '+' '.join(str(v)+' 0' for v in matrix)+'\n[End]\n'
for name,matrix in [('thru',[0,1,1,0]),('opaque',[0,0,0,0]),('ordinary',[.1,.2,.3,.1])]:
 (OUT/(name+'.s2p')).write_text(fixture(matrix),encoding='ascii')
options={'left_file':str(OUT/'thru.s2p'),'right_file':str(OUT/'thru.s2p')}
(OUT/'options.json').write_text(json.dumps(options)+'\n',encoding='ascii')
records=[]
for name,command,file in [('opaque-parse','inspect','opaque.s2p'),('opaque-deembed','deembed','opaque.s2p'),('ordinary-deembed','deembed','ordinary.s2p')]:
 args=['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/touchstone.mjs'),command,str(OUT/file)]
 if command=='deembed':args.append('@'+str(OUT/'options.json'))
 run=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
 for stream in ['stdout','stderr']:(OUT/(name+'.before.'+stream+'.log')).write_text(getattr(run,stream),encoding='utf-8')
 records.append({'name':name,'command':args,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
assert records[0]['exitCode']==records[2]['exitCode']==0
assert records[1]['exitCode']==2 and 'division by zero' in records[1]['stderr']
report={'status':'reproduced','actualFileCLINodeProcesses':3,'records':records,'bridgeSHA256':sha(bridge),'inputSHA256':{p.name:sha(p) for p in OUT.glob('*.s2p')},'independentExpected':'Ideal through left/right fixtures act as identity on every finite DUT S matrix, including the passive matched opaque matrix S=0. The finite recovered S must remain exactly0.','nodeCompileCacheDisabled':True,'temporaryDirectory':str(temp),'sdkToolsExecuted':0}
(OUT/'BASELINE.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
for row in records:print(row['name'],row['exitCode'],row['stderr'].strip(),row['stdout'][:100].strip())
