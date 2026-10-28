import hashlib,json,os,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]/'projects/moonbit-touchstone'
assert not (OUT/'BASELINE.json').exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
bridge=ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
assert sha(bridge)==json.loads((OUT/'COMPILED-BEFORE.json').read_text())['sha256']
assert 'zero complex denominator' in (OUT/'opaque-deembed.before.stderr.log').read_text()
assert not (OUT/'opaque-parse.before.stderr.log').read_text() and not (OUT/'ordinary-deembed.before.stderr.log').read_text()
command=['C:/Program Files/nodejs/node.exe',str(ROOT/'tools/touchstone.mjs'),'deembed',str(OUT/'opaque.s2p'),'@'+str(OUT/'options.json')]
env=dict(os.environ,NODE_DISABLE_COMPILE_CACHE='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(OUT/'runtime-temp'),TMP=str(OUT/'runtime-temp'))
run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
for stream in ['stdout','stderr']:(OUT/('opaque-deembed-confirmed.before.'+stream+'.log')).write_text(getattr(run,stream),encoding='utf-8')
report={'status':'reproduced','initialActualFileCLINodeProcesses':3,'focusedDiagnosticRecoveryProcesses':1,'actualFileCLINodeProcesses':4,'initialHarnessFailure':'After three processes, the diagnostic assertion expected division by zero; actual message is zero complex denominator. Exit-code list was not serialized before that assertion. Existing success controls are not rerun.','initialControls':{'parseExitCode':0,'ordinaryExitCode':0,'exitProvenance':'Both established by the original harness assertion preceding its diagnostic failure','ordinaryStdout':(OUT/'ordinary-deembed.before.stdout.log').read_text()},'confirmedDefect':{'command':command,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr},'bridgeSHA256':sha(bridge),'inputSHA256':{p.name:sha(p) for p in OUT.glob('*.s2p')},'independentExpected':'Ideal through fixtures must leave a finite opaque passive DUT S=0 unchanged; the fixture chain matrices are invertible. No measured T representation is needed to define this physical deembedding.','nodeCompileCacheDisabled':True,'sdkToolsExecuted':0}
(OUT/'BASELINE.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
assert run.returncode==2 and 'zero complex denominator' in run.stderr
print('Confirmed legal opaque DUT error:',run.returncode,run.stderr.strip(),'; total baseline Node processes=4')
