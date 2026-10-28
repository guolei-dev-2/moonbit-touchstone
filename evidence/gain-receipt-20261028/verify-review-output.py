import hashlib,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]/'projects/moonbit-touchstone'
source=ROOT/'examples/power-gain.s2p';saved=OUT/'workflow-first-cases/fail.json';output=OUT/'review-output.json'
assert not output.exists()
argv=['node','tools/touchstone.mjs','gain-review',str(source),'@'+str(saved),str(output)]
commands=[]
def call(expected):
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8');commands.append({'command':argv,'exitCode':r.returncode,'expectedExitCode':expected,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==expected
 return r
first=call(0);assert first.stdout=='' and output.exists()
review=json.loads(output.read_text(encoding='utf-8'));assert review['status']=='reproduced' and review['recorded_status']==review['current_status']=='fail'
before=hashlib.sha256(output.read_bytes()).hexdigest();second=call(2);assert hashlib.sha256(output.read_bytes()).hexdigest()==before
result={'complete':True,'CLIProcesses':2,'workflowChecks':2,'commands':commands,'savedReviewSHA256':before,
 'checks':['CLI review saved full reproduced-fail JSON','Existing review output preserved on rejected overwrite'],
 'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['cmd/bridge/main.mbt','tools/touchstone.mjs']}}
(OUT/'review-output-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'complete':True,'CLIProcesses':2,'workflowChecks':2}))
