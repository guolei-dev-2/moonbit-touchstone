"""Actual gain-record/gain-review workflow, independently checked by hashlib.

No RF numerical oracle is rerun. Frozen11 plain results are reused to verify
legacy output/payload preservation. New checks concern byte identity, effective
requests, exact JSON replay/mismatch and exit/IO behavior. Optional NXP input is
read in place; only its receipt summary is retained, no model/full GT export.
"""
import argparse,copy,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools/touchstone.mjs'
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--vendor-input',type=Path);args=p.parse_args()
if args.evidence.exists():p.error('use fresh evidence path')
work=args.evidence.parent/(args.evidence.stem+'-cases');work.mkdir(exist_ok=False)
commands=[];checks=[];artifacts=[];vendor=None
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
 file=work/name;assert not file.exists();file.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='ascii');artifacts.append(file);return file
def run(command,input,options,expected,label,output=None):
 argv=['node',str(TOOL),command,str(input),options if isinstance(options,str) else json.dumps(options)]
 if output:argv.append(str(output))
 result=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
 commands.append({'label':label,'command':argv,'exitCode':result.returncode,'expectedExitCode':expected,'stderr':result.stderr})
 assert result.returncode==expected,(label,result.returncode,result.stderr,result.stdout)
 if expected==2:return result
 if output:
  assert result.stdout=='' and output.exists();artifacts.append(output);return json.loads(output.read_text(encoding='utf-8'))
 return json.loads(result.stdout)
def record(input,options,status,name):
 output=work/(name+'.json');assert not output.exists()
 receipt=run('gain-record',input,options,{'pass':0,'fail':3,'inconclusive':4}[status],'record '+name,output)
 assert set(receipt)=={'schema','input','request','result'} and receipt['schema']=='touchstone.gain-receipt.v1'
 assert receipt['input']=={'sha256':digest(input),'bytes':len(input.read_bytes())}
 request=receipt['request'];result=receipt['result'];assert request['command']=='gain-check' and result['status']==status
 assert request['terminal_mode']==result['terminal_mode']
 for key,value in result['matching'].items():assert request[key]==value
 for key in ['start_hz','end_hz','minimum_db','maximum_db']:
  assert request.get(key)==result['report'].get(key)
 assert all('file' not in key and 'path' not in key for key in request)
 checks.append({'label':'record '+name,'inputSHA256':digest(input),'bytes':receipt['input']['bytes'],'analysisStatus':status,'request':request})
 return output,receipt
def review(input,receipt_path,status,analysis,label,sections=None):
 result=run('gain-review',input,'@'+str(receipt_path),0 if status=='reproduced' else 5,label)
 assert result['kind']=='gain_receipt_replay' and result['status']==status and result['recorded_status']==analysis
 source=json.loads(receipt_path.read_text(encoding='utf-8'));actual={'sha256':digest(input),'bytes':len(input.read_bytes())}
 assert result['input']['actual']==actual
 assert result['input']['recorded']=={'sha256':source['input']['sha256'].lower(),'bytes':source['input']['bytes']}
 if status=='input_mismatch':
  assert result['input_match'] is False and result['result_match'] is None and result['current_status'] is None and result['current_result'] is None
 else:
  assert result['input_match'] is True and result['result_match']==(status=='reproduced')
  assert result['current_status']==result['current_result']['status']
  if status=='reproduced':assert result['current_status']==analysis and result['current_result']==source['result'] and not result['changed_sections']
 if sections is not None:assert set(result['changed_sections'])==set(sections),(label,result['changed_sections'],sections)
 checks.append({'label':label,'status':status,'recordedStatus':analysis,'currentStatus':result['current_status'],'changedSections':result['changed_sections']})
 return result
failure=None
try:
 sample=ROOT/'examples/power-gain.s2p';full={'start_hz':1e9,'end_hz':2e9};bundles={}
 scenarios=[('pass',{**full,'minimum_db':3.,'maximum_db':7.},'pass'),
  ('fail',{**full,'terminal_mode':'impedance','source_ohms':[100.,20.],'load_ohms':[25.,-10.],'minimum_db':4.,'maximum_db':7.},'fail'),
  ('inconclusive',{'start_hz':1e9,'end_hz':3e9,'minimum_db':3.},'inconclusive'),
  ('zero-lower',{'start_hz':1e9,'end_hz':1e9,'minimum_db':0.,'maximum_db':7.},'pass')]
 for name,options,status in scenarios:
  file,bundle=record(sample,options,status,name);assert bundle['request']['ports']==2
  review(sample,file,'reproduced',status,'replay '+name);bundles[name]=(file,bundle,options)
 assert bundles['zero-lower'][1]['request']['minimum_db']==0
 zero=work/'zero.s2p';zero.write_bytes(b'# Hz S RI R 50\n1 0 0 0 0 0 0 0 0\n2 0 0 0 0 0 0 0 0\n');artifacts.append(zero)
 zero_path,zero_bundle=record(zero,{'start_hz':1.,'end_hz':2.,'maximum_db':0.},'pass','zero-upper')
 assert zero_bundle['request']['maximum_db']==0
 review(zero,zero_path,'reproduced','pass','replay zero upper')
 crlf=work/'crlf.s2p';crlf.write_bytes(sample.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'));artifacts.append(crlf)
 crlf_path,crlf_bundle=record(crlf,scenarios[0][1],'pass','crlf')
 assert crlf_bundle['input']['sha256']!=digest(sample)
 review(crlf,crlf_path,'reproduced','pass','replay raw CRLF')
 review(sample,crlf_path,'input_mismatch','pass','line endings are byte identity')
 v2=work/'versioned.ts';v2.write_bytes(b'[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 2\n[Two-Port Data Order] 12_21\n[Network Data]\n1000000000 .25 0 .125 0 2 0 -.25 0\n2000000000 .2 0 .1 0 1.5 0 -.2 0\n[End]\n');artifacts.append(v2)
 v2_path,v2_bundle=record(v2,scenarios[0][1],'pass','versioned');assert 'ports' not in v2_bundle['request']
 review(v2,v2_path,'reproduced','pass','replay versioned without hint')
 renamed=work/'renamed input.s8p';renamed.write_bytes(sample.read_bytes());artifacts.append(renamed)
 review(renamed,bundles['pass'][0],'reproduced','pass','recorded hint survives rename')
 base_path,base,base_options=bundles['fail']
 changed=work/'changed-invalid.s2p';changed.write_bytes(b'X'*len(sample.read_bytes()));artifacts.append(changed)
 review(changed,base_path,'input_mismatch','fail','different same-size invalid model stops before parse')
 appended=work/'changed-comment.s2p';appended.write_bytes(sample.read_bytes()+b'! later comment\n');artifacts.append(appended)
 review(appended,base_path,'input_mismatch','fail','changed source size and digest')
 def reverse_objects(value):
  if isinstance(value,dict):return {k:reverse_objects(value[k]) for k in reversed(list(value))}
  if isinstance(value,list):return [reverse_objects(x) for x in value]
  return value
 reordered=save('reordered.json',reverse_objects(base));review(sample,reordered,'reproduced','fail','JSON order and formatting ignored')
 upper=copy.deepcopy(base);upper['input']['sha256']=upper['input']['sha256'].upper()
 review(sample,save('uppercase-hash.json',upper),'reproduced','fail','hexadecimal case preserved semantically')
 mutants=[]
 changed_status=copy.deepcopy(base);changed_status['result']['status']='pass';mutants.append(('changed status',changed_status,'pass',['status']))
 changed_summary=copy.deepcopy(base);changed_summary['result']['report']['lowest']['gain_db']+=1.;mutants.append(('changed summary',changed_summary,'fail',['report']))
 changed_matching=copy.deepcopy(base);changed_matching['result']['matching']['source_ohms'].reverse();mutants.append(('changed matching',changed_matching,'fail',['matching']))
 changed_request=copy.deepcopy(base);changed_request['request']['maximum_db']=8.;mutants.append(('changed request',changed_request,'fail',['report']))
 for i,(label,bundle,analysis,sections) in enumerate(mutants):review(sample,save('result-mutant-'+str(i)+'.json',bundle),'result_mismatch',analysis,label,sections)
 wrong_hash=copy.deepcopy(base);wrong_hash['input']['sha256']='0'*64
 review(sample,save('wrong-hash.json',wrong_hash),'input_mismatch','fail','recorded hash mismatch')
 wrong_size=copy.deepcopy(base);wrong_size['input']['bytes']+=1
 review(sample,save('wrong-size.json',wrong_size),'input_mismatch','fail','recorded byte-count mismatch')
 invalid=[]
 future=copy.deepcopy(base);future['schema']='touchstone.gain-receipt.v2';invalid.append(('unsupported schema',future))
 missing=copy.deepcopy(base);del missing['input'];invalid.append(('missing input identity',missing))
 bad_hash=copy.deepcopy(base);bad_hash['input']['sha256']='not-hex';invalid.append(('invalid digest',bad_hash))
 bad_size=copy.deepcopy(base);bad_size['input']['bytes']=-1;invalid.append(('invalid size',bad_size))
 other_command=copy.deepcopy(base);other_command['request']['command']='gain-review';invalid.append(('arbitrary replay rejected',other_command))
 extra=copy.deepcopy(base);extra['note']='annotation belongs outside envelope';invalid.append(('unknown envelope field',extra))
 nested_path=copy.deepcopy(base);nested_path['request']['left_file']=str(work/'must-not-be-read.txt');invalid.append(('nested fixture path rejected',nested_path))
 for i,(label,bundle) in enumerate(invalid):
  file=save('invalid-'+str(i)+'.json',bundle);r=run('gain-review',sample,'@'+str(file),2,label)
  if label=='nested fixture path rejected':assert 'left_file' in r.stderr and 'ENOENT' not in r.stderr
 legacy=save('legacy-plain.json',base['result']);r=run('gain-review',sample,'@'+str(legacy),2,'legacy report has no identity');assert 'gain-record' in r.stderr
 run('gain-review',sample,'[]',2,'non-object receipt rejected')
 run('gain-record',sample,{**full,'min_db':3.},2,'record invalid query rejected')
 preserved=digest(bundles['pass'][0]);run('gain-record',sample,scenarios[0][1],2,'receipt exclusive output',bundles['pass'][0]);assert digest(bundles['pass'][0])==preserved
 # Old plain command payloads are compared with frozen11, without rerunning
 # its39-request collection or any old numerical oracle.
 frozen=json.loads((ROOT/'evidence/gain-check-20261028/independent-first.json').read_text(encoding='utf-8'))
 gamma_expected=next(x['response']['result'] for x in frozen['raw'] if x['label']=='gamma pass')
 ohm_expected=json.loads((ROOT/'evidence/gain-check-20261028/independent-first-cli-fail.json').read_text(encoding='utf-8'))
 assert bundles['pass'][1]['result']==gamma_expected and base['result']==ohm_expected
 for label,options,expected,status in [('legacy gamma',scenarios[0][1],gamma_expected,0),('legacy ohm',base_options,ohm_expected,3)]:
  plain=run('gain-check',sample,options,status,label);assert plain==expected and 'schema' not in plain
  checks.append({'label':label,'frozen11PayloadPreserved':True})
 if args.vendor_input:
  digest_vendor=digest(args.vendor_input);assert digest_vendor=='d4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95'
  options={'start_hz':40000000.,'end_hz':6000000000.,'minimum_db':2.,'maximum_db':30.}
  frozen_vendor=next(x for x in frozen['checks'] if x['label']=='NXP aggregate report')
  file,bundle=record(args.vendor_input,options,frozen_vendor['expectedStatus'],'vendor-receipt')
  report=bundle['result']['report'];reference=frozen_vendor['reference']
  for key in ['status','sample_count','state_counts','below_minimum_count','above_maximum_count','range_covered']:assert report[key]==reference[key]
  review(args.vendor_input,file,'reproduced',bundle['result']['status'],'vendor identity and replay')
  vendor={'sha256':digest_vendor,'receiptInputBytes':bundle['input']['bytes'],'analysisSamples':report['sample_count'],
   'newNumericComparisons':0,'scope':'Byte identity, normalized request and replay only; frozen11 aggregate expected status/counts reused.'}
except Exception as e:failure=e
finally:
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'CLIProcesses':len(commands),'workflowChecks':len(checks),'commands':commands,'checks':checks,'vendor':vendor,
  'oracle':'Independent Python hashlib raw-byte identity, exact protocol assertions and mutation truth cases; frozen11 payloads reused, not RF oracle rerun.',
  'caseDirectory':str(work),'artifacts':[{'path':str(file),'sha256':digest(file)} for file in artifacts if file.exists()],
  'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['cmd/bridge/main.mbt','tools/touchstone.mjs','examples/gain_receipt_demo.mjs','tools/verify-gain-receipt.py','gain.mbt','gain_impedance.mbt','gain_band.mbt']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','CLIProcesses','workflowChecks']},indent=2))
if failure:raise failure
