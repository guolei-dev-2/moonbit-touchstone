#!/usr/bin/env python3
"""File workflow checks with an independent full four-port wave reference."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
parser.add_argument('--baseline',type=Path,default=ROOT/'evidence/terminate-file-20261028/BASELINE.json');args=parser.parse_args()
assert not args.evidence.exists()
work=args.evidence.with_name(args.evidence.stem+'-cases');work.mkdir()
base=json.loads(args.baseline.read_text(encoding='utf-8'));spec=base['networkSpecification']
source=ROOT/'examples/loaded-four-port.ts';frequencies=spec['frequency_hz'];refs=spec['reference_ohms']
matrices=[[[complex(*m[i*4+j]) for j in range(4)] for i in range(4)] for m in spec['sRowMajor']]
terminals={'source_ohms':[100.,20.],'load_ohms':[30.,-12.]}
commands=[];checks=[];artifacts=[];failure=None;point_checks=0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,text):
 p=work/name;p.write_text(text,encoding='ascii',newline='');artifacts.append(p);return p
def solve(a,b):
 a=[list(row)+[rhs] for row,rhs in zip(a,b)];n=len(b)
 for col in range(n):
  pivot=max(range(col,n),key=lambda i:abs(a[i][col]));assert a[pivot][col]!=0
  a[col],a[pivot]=a[pivot],a[col];divisor=a[col][col];a[col]=[v/divisor for v in a[col]]
  for i in range(n):
   if i!=col:
    factor=a[i][col];a[i]=[x-factor*y for x,y in zip(a[i],a[col])]
 return [row[-1] for row in a]
def expected_gain(s,loads):
 zs=complex(*terminals['source_ohms']);zl=complex(*terminals['load_ohms'])
 gamma=[(zs-refs[0])/(zs+refs[0]),0j,0j,(zl-refs[3])/(zl+refs[3])]
 for port,re,im in loads['terminations']:
  z=complex(re,im);gamma[port]=(z-refs[port])/(z+refs[port]) if loads.get('impedance',False) else z
 system=[[int(i==j)-gamma[i]*s[i][j] for j in range(4)] for i in range(4)]
 forcing=[math.sqrt(refs[0])/(zs+refs[0]),0j,0j,0j]
 incident=solve(system,forcing);outgoing=sum(s[3][j]*incident[j] for j in range(4))
 gain=4.*zs.real*(1.-abs(gamma[3])**2)*abs(outgoing)**2
 return {'gain':gain,'gain_db':10.*math.log10(gain)}
def close(actual,expected,label):assert math.isfinite(actual) and abs(actual-expected)<=max(4e-11,abs(expected)*4e-12),(label,actual,expected)
def call(command,input,options,expected,label,output=None):
 argv=['node',str(ROOT/'tools/touchstone.mjs'),command,str(input),json.dumps(options)]+([str(output)] if output else [])
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
 log=save(label+'.stdout.txt',r.stdout)
 item={'label':label,'argv':argv,'exitCode':r.returncode,'expectedExitCode':expected,'stderr':r.stderr,'stdout':str(log)}
 commands.append(item);assert r.returncode==expected,(label,r.returncode,r.stderr)
 if expected==2:assert not r.stdout,label
 else:assert not r.stderr,(label,r.stderr)
 if output and expected!=2:
  assert not r.stdout and output.exists();artifacts.append(output);return output.read_text(encoding='ascii')
 return r.stdout
def check_gain(file,options,label):
 global point_checks
 actual=json.loads(call('transducer-gain-impedance',file,terminals,0,label))
 reference=[expected_gain(s,options) for s in matrices];assert len(actual)==2
 for i,(value,want) in enumerate(zip(actual,reference)):
  assert value['state']=='finite' and value['frequency_hz']==frequencies[i]
  close(value['gain'],want['gain'],(label,i,'gain'));close(value['gain_db'],want['gain_db'],(label,i,'db'));point_checks+=1
 checks.append({'label':label,'pointComparisons':2,'reference':reference,'actual':actual,
  'oracle':'Full original four-port incident-wave linear equations with every attached load, source and output termination'})
 return actual,reference
try:
 assert sha(source)==base['inputSHA256']
 physical=base['options'];reduced=work/'physical reduced.ts'
 call('terminate-file',source,physical,0,'physical-file-export',reduced)
 info=json.loads(call('inspect',reduced,{},0,'physical-readback-metadata'))
 assert info['ports']==2 and info['reference_ohms']==[50,75] and info['frequency_hz']==frequencies
 assert info['information']==['Synthetic four-port path; terminate original ports 1 and 2.']
 assert info['noise']==[] and info['mixed_mode_order']==[]
 dumped=json.loads(call('dump',reduced,{},0,'physical-readback-network'))
 for key,value in base['oldReducedNetwork'].items():assert dumped[key]==value,key
 checks.append({'label':'file-roundtrip-original-port-order-0-3-and-information','oldJSONNetworkReadbackEqual':True})
 actual,expected=check_gain(reduced,physical,'physical-loaded-GT')
 query={'terminal_mode':'impedance',**terminals,'start_hz':frequencies[0],'end_hz':frequencies[-1],'minimum_db':3.,'maximum_db':10.}
 assert expected[0]['gain_db']>3. and expected[1]['gain_db']<3.
 receipt_path=work/'reduced-gain-receipt.json'
 receipt=json.loads(call('gain-record',reduced,query,3,'reduced-file-gain-record',receipt_path))
 assert receipt['input']=={'sha256':sha(reduced),'bytes':reduced.stat().st_size}
 assert receipt['result']['status']=='fail' and receipt['result']['report']['lowest']['point']==1
 assert receipt['result']['reference_ohms']==[50,75]
 reviewed=json.loads(call('gain-review',reduced,receipt,0,'reduced-file-gain-review'))
 assert reviewed['status']=='reproduced' and reviewed['recorded_status']==reviewed['current_status']=='fail'
 checks.append({'label':'exported-file-to-existing-band-receipt-review','boundInput':'reduced file only','analysisStatus':'fail','reviewStatus':'reproduced'})
 gamma={'terminations':[[1,1.25,0.],[2,.25,-.1]]}
 text=call('terminate-file',source,gamma,0,'Gamma-active-load-stdout');assert text.startswith('[Version] 2.1')
 gamma_file=save('Gamma-reduced.ts',text);check_gain(gamma_file,gamma,'Gamma-loaded-GT')
 identity=work/'identity.ts';call('terminate-file',source,{'terminations':[]},0,'empty-load-list',identity)
 original=json.loads(call('dump',identity,{},0,'identity-readback'))
 assert original['ports']==4 and original['reference_ohms']==refs and original['frequency_hz']==frequencies
 assert [[[v['re'],v['im']] for v in point] for point in original['values']]==spec['sRowMajor']
 checks.append({'label':'empty-termination-identity-retains-entire-network','ports':4})
 mixed=work/'mixed-source.ts';call('mixed',source,{'pairs':[[0,1]]},0,'prepare-mixed-input',mixed)
 # Older mixed CLI versions omitted information; add it only when absent so
 # this fixture also accepts the corrected metadata-preserving producer.
 mixed_text=mixed.read_text(encoding='ascii')
 if '[Begin Information]' not in mixed_text:
  mixed.write_text(mixed_text.replace('[Network Data]',
   '[Begin Information]\n'+info['information'][0]+'\n[End Information]\n[Network Data]'),encoding='ascii',newline='')
 mixed_reduced=work/'mixed-reduced.ts';call('terminate-file',mixed,physical,0,'mixed-input-file-export',mixed_reduced)
 mixed_info=json.loads(call('inspect',mixed_reduced,{},0,'mixed-export-is-single-ended'))
 assert mixed_info['ports']==2 and mixed_info['mixed_mode_order']==[] and mixed_info['reference_ohms']==[50,75]
 assert mixed_info['information']==info['information'];check_gain(mixed_reduced,physical,'mixed-file-loaded-GT')
 preserved=sha(reduced);call('terminate-file',source,physical,2,'existing-output-preserved',reduced);assert sha(reduced)==preserved
 checks.append({'label':'exclusive-output-no-overwrite','sha256':preserved})
 invalid=[('missing-terminations',{}),('malformed-triple',{'terminations':[[1,0.]]}),
  ('fractional-port',{'terminations':[[1.5,0.,0.]]}),('duplicate-port',{'terminations':[[1,0.,0.],[1,.2,0.]]}),
  ('out-of-range-port',{'terminations':[[4,0.,0.]]}),('all-ports-removed',{'terminations':[[p,0.,0.] for p in range(4)]}),
  ('unknown-option',{**physical,'unit':'ohm'}),('fixture-path-not-read',{**physical,'left_file':str(work/'must-not-read.txt')}),
  ('impedance-type',{**physical,'impedance':'true'})]
 for label,options in invalid:
  forbidden=work/(label+'.ts');call('terminate-file',source,options,2,label,forbidden);assert not forbidden.exists()
  if label=='fixture-path-not-read':assert 'left_file' in commands[-1]['stderr'] and 'ENOENT' not in commands[-1]['stderr']
  checks.append({'label':label,'rejectedWithoutOutput':True})
 noisy=save('noise.ts','[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 21_12\n[Number of Frequencies] 1\n[Number of Noise Frequencies] 1\n[Network Data]\n900000000 .1 0 .2 0 .3 0 .1 0\n[Noise Data]\n900000000 2 .25 0 5\n[End]\n')
 noisy_output=work/'must-not-drop-noise.ts';call('terminate-file',noisy,{'terminations':[[1,0,0]]},2,'noise-not-silently-discarded',noisy_output)
 assert 'noise' in commands[-1]['stderr'] and not noisy_output.exists()
 checks.append({'label':'noise-not-silently-discarded','rejectedWithoutOutput':True})
 singular=save('singular.s2p','# Hz S RI R 50\n1 0 0 0 0 0 0 1 0\n');bad_loop=work/'must-not-write-singular.ts'
 call('terminate-file',singular,{'terminations':[[1,1,0]]},2,'singular-feedback',bad_loop);assert not bad_loop.exists()
 checks.append({'label':'singular-feedback','rejectedWithoutOutput':True})
 old=json.loads(call('terminate',source,physical,0,'legacy-terminate-JSON-preserved'));assert old==base['oldReducedNetwork'] and 'text' not in old
 checks.append({'label':'legacy-terminate-JSON-preserved','equalToPreImplementationBaseline':True})
 assert sha(source)==base['inputSHA256']
except Exception as exc:failure=exc
finally:
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'actualCLIProcesses':len(commands),'consumerChecks':len(checks),
  'independentGTPointComparisons':point_checks,'commands':commands,'checks':checks,
  'oldNumericalOrReceiptCollectionsRerun':False,'newManufacturerInputs':0,
  'artifacts':[{'path':str(p),'sha256':sha(p)} for p in artifacts if p.exists()],
  'sourceSHA256':{k:sha(ROOT/k) for k in ['cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-terminate-file.py','examples/loaded-four-port.ts',
   'examples/terminate-four-port.json','examples/terminated-gain-check.json','examples/terminate_file_demo.mjs','amplifier.mbt','gain.mbt','gain_impedance.mbt','gain_band.mbt']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['complete','failure','actualCLIProcesses','consumerChecks','independentGTPointComparisons']}))
if failure:raise failure
