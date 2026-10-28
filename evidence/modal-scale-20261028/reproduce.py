import hashlib
import json
import os
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]/'projects/moonbit-touchstone'
assert not (OUT/'BASELINE.json').exists()
env = dict(os.environ, NODE_DISABLE_COMPILE_CACHE='1', PYTHONDONTWRITEBYTECODE='1')
temp = OUT/'runtime-temp'
temp.mkdir(exist_ok=False)
env['TMP'] = env['TEMP'] = str(temp)
bridge = ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(bridge) == json.loads((OUT/'COMPILED-BEFORE.json').read_text())['sha256']

def fixture(value):
    matrix = [(0.0,0.0)]*16
    matrix[4] = matrix[14] = value
    rows = [' '.join(str(v) for z in matrix[row*4:(row+1)*4] for v in z) for row in range(4)]
    return '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 4\n[Number of Frequencies] 1\n[Mixed-Mode Order] D1,2 D3,4 C1,2 C3,4\n[Network Data]\n1000000000 '+rows[0]+'\n'+'\n'.join(rows[1:])+'\n[End]\n'

options = {'output_pair':1, 'input_pair':0, 'cmrr':'balanced'}
(OUT/'options.json').write_text(json.dumps(options)+'\n', encoding='ascii')
for name, value in [('large',(1.5e308,1.5e308)),('ordinary',(.5,.5))]:
    (OUT/(name+'.s4p')).write_text(fixture(value),encoding='ascii')
records=[]
for name, command, file in [('large-parse','inspect','large.s4p'),('large-metrics','modal-metrics','large.s4p'),('ordinary-metrics','modal-metrics','ordinary.s4p')]:
    args=['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/touchstone.mjs'),command,str(OUT/file)]
    if command=='modal-metrics':args.append('@'+str(OUT/'options.json'))
    run=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    for stream in ['stdout','stderr']:(OUT/(name+'.before.'+stream+'.log')).write_text(getattr(run,stream),encoding='utf-8')
    records.append({'name':name,'command':args,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
assert records[0]['exitCode']==records[2]['exitCode']==0
report={'records':records,'actualFileCLINodeProcesses':3,'bridgeSHA256':sha(bridge),'inputSHA256':{name:sha(OUT/name) for name in ['large.s4p','ordinary.s4p']},'independentExpected':'Balanced Sdd21/Scc21=1 exactly, hence CMRR=0dB; each loss is finite -20log10(sqrt(2)*1.5e308), evaluable without linear magnitude overflow','nodeCompileCacheDisabled':True,'tempDirectory':str(temp),'sdkToolsExecuted':0}
(OUT/'BASELINE.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
for row in records:print(row['name'],row['exitCode'],row['stdout'][:420].strip(),row['stderr'].strip())
