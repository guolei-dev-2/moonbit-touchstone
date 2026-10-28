#!/usr/bin/env python3
"""Independent CSV consumer; no RF oracle or unchanged test collection rerun."""
import argparse,csv,hashlib,io,json,math,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HEADERS='point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,maximum_db,below_minimum,above_maximum,sample_status,report_status,range_covered'.split(',')
parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
assert not args.evidence.exists()
work=args.evidence.with_name(args.evidence.stem+'-cases');work.mkdir()
commands=[];checks=[];artifacts=[];failure=None
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,text):
 p=work/name;p.write_text(text,encoding='ascii',newline='');artifacts.append(p);return p
def run(command,source,options,code,label,output=None):
 opts=json.dumps(options) if isinstance(options,dict) else options
 argv=['node',str(ROOT/'tools/touchstone.mjs'),command,str(source),opts]+([str(output)] if output else [])
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
 commands.append({'label':label,'command':argv,'exitCode':r.returncode,'expectedExitCode':code,'stderr':r.stderr})
 assert r.returncode==code,(label,r.returncode,r.stderr)
 if code==2:assert not r.stdout,label
 else:assert not r.stderr,(label,r.stderr)
 return r
def table(text,label,options,expected,status,covered=True):
 assert text.encode('ascii') and '\r' not in text and text.endswith('\n'),label
 reader=csv.DictReader(io.StringIO(text,newline=''));assert reader.fieldnames==HEADERS,label
 rows=list(reader);assert len(rows)==len(expected),(label,len(rows),len(expected))
 for row,want in zip(rows,expected):
  assert set(row)==set(HEADERS) and None not in row.values(),(label,row)
  assert row['report_status']==status and row['range_covered']==str(covered).lower(),(label,row)
  for key in ['start_hz','end_hz','minimum_db','maximum_db']:
   assert (float(row[key])==options[key]) if key in options else row[key]=='',(label,key,row[key])
  for key in ['frequency_hz','gain','gain_db']:
   if row[key]!='':assert math.isfinite(float(row[key])),(label,key)
  for key,value in want.items():assert row[key]==str(value),(label,key,row[key],value)
 checks.append({'label':label,'rows':len(rows),'reportStatus':status,'rangeCovered':covered,
  'pointIndices':[int(r['point']) for r in rows],'states':[r['state'] for r in rows]})
 return rows
def row(point,hz,state,below,above,status):
 return {'point':point,'frequency_hz':hz,'state':state,'below_minimum':below,'above_maximum':above,'sample_status':status}
def exported(source,options,code,label,wanted,status,covered=True,output=None):
 r=run('gain-csv',source,options,code,label,output)
 if output:
  assert not r.stdout and output.exists();artifacts.append(output);text=output.read_text(encoding='ascii')
 else:text=r.stdout;save(label+'.csv',text)
 return table(text,label,options,wanted,status,covered)
def reference_cells(rows,observations):
 by_hz={x['frequency_hz']:x for x in observations}
 for value in rows:
  ref=by_hz[float(value['frequency_hz'])];assert value['state']==ref['state']
  for key in ['gain','gain_db']:
   assert (float(value[key])==ref[key]) if key in ref else value[key]=='',(key,value,ref)

try:
 sample=ROOT/'examples/power-gain.s2p'
 frozen_dir=ROOT/'evidence/gain-receipt-20261028'
 frozen={name:json.loads((frozen_dir/('receipt-'+name+'.json')).read_text(encoding='utf-8')) for name in ['pass','fail','inconclusive']}
 full={'start_hz':1e9,'end_hz':2e9,'minimum_db':3.,'maximum_db':7.}
 gamma=exported(sample,full,0,'gamma-pass',[row(0,1000000000,'finite','false','false','pass'),row(1,2000000000,'finite','false','false','pass')],'pass')
 reference_cells(gamma,[frozen['pass']['result']['report'][k] for k in ['lowest','highest']])
 ohms={**full,'terminal_mode':'impedance','source_ohms':[100.,20.],'load_ohms':[25.,-10.],'minimum_db':4.}
 output=work/'saved failing table.csv'
 ohm_rows=exported(sample,ohms,3,'ohm-fail-saved',[row(0,1000000000,'finite','false','false','pass'),row(1,2000000000,'finite','true','false','fail')],'fail',output=output)
 reference_cells(ohm_rows,[frozen['fail']['result']['report'][k] for k in ['lowest','highest']])
 inconclusive={'start_hz':1e9,'end_hz':3e9,'minimum_db':3.}
 exported(sample,inconclusive,4,'incomplete-band',[row(0,1000000000,'finite','false','false','pass'),row(1,2000000000,'finite','false','false','pass')],'inconclusive',False)
 exported(sample,{'start_hz':1.1e9,'end_hz':1.9e9,'minimum_db':0.},4,'no-selected-samples',[],'inconclusive')
 exported(sample,{'start_hz':2e9,'end_hz':2e9,'maximum_db':4.},0,'single-original-index',[row(1,2000000000,'finite','false','false','pass')],'pass')
 zero=save('zero.s2p','# Hz S RI R 50\n1 0 0 0 0 0 0 0 0\n2 0 0 0 0 0 0 0 0\n')
 zeros=[{**row(i,i+1,'zero','false','false','pass'),'gain':'0','gain_db':''} for i in range(2)]
 exported(zero,{'start_hz':1.,'end_hz':2.,'maximum_db':0.},0,'zero-upper',zeros,'pass')
 zeros_lower=[{**r,'below_minimum':'true','sample_status':'fail'} for r in zeros]
 exported(zero,{'start_hz':1.,'end_hz':2.,'minimum_db':0.},3,'zero-lower',zeros_lower,'fail')
 mixed=save('mixed five states.s2p','# Hz S RI R 50\n1 0 0 2 0 0 0 0 0\n2 0 0 0 0 0 0 0 0\n3 0 0 1e-200 0 0 0 0 0\n4 0 0 1e200 0 0 0 0 0\n5 2 0 1 0 0 0 0 0\n')
 mixed_options={'source':[.5,0.],'start_hz':1.,'end_hz':5.,'minimum_db':-3000.,'maximum_db':3000.}
 wanted=[row(0,1,'finite','false','false','pass'),{**row(1,2,'zero','true','false','fail'),'gain':'0','gain_db':''},
  {**row(2,3,'underflow','true','false','fail'),'gain':'0'}, {**row(3,4,'overflow','false','true','fail'),'gain':''},
  {**row(4,5,'singular','','','unknown'),'gain':'','gain_db':''}]
 mixed_rows=exported(mixed,mixed_options,3,'five-state-fail',wanted,'fail')
 assert float(mixed_rows[2]['gain_db']) < -3000 and float(mixed_rows[3]['gain_db']) > 3000
 upper_options={'source':[.5,0.],'start_hz':1.,'end_hz':5.,'maximum_db':5000.}
 upper_wanted=[{**r,'below_minimum':'false','above_maximum':'false','sample_status':'pass'} if r['state']!='singular' else r for r in wanted]
 exported(mixed,upper_options,4,'singular-remains-unknown',upper_wanted,'inconclusive')
 exported(mixed,{'source':[.5,0.],'start_hz':5.,'end_hz':5.,'maximum_db':0.},4,'only-singular',[wanted[4]],'inconclusive')
 exported(mixed,{'source':[.5,0.],'start_hz':3.,'end_hz':4.,'minimum_db':-5000.,'maximum_db':5000.},0,'positive-extremes-known',
  [{**wanted[2],'below_minimum':'false','sample_status':'pass'},{**wanted[3],'above_maximum':'false','sample_status':'pass'}],'pass')
 exported(mixed,{'source':[.5,0.],'start_hz':0.,'end_hz':1.,'maximum_db':10.},4,'local-pass-global-inconclusive',[wanted[0]],'inconclusive',False)
 large=save('capacity.s2p','# Hz S RI R 50\n'+''.join(str(i)+' 0 0 1 0 0 0 0 0\n' for i in range(100000)))
 large_run=run('gain-csv',large,{'start_hz':0.,'end_hz':99999.,'maximum_db':0.},0,'full-100000-sample-CSV')
 large_csv=save('capacity.csv',large_run.stdout)
 reader=csv.DictReader(io.StringIO(large_run.stdout,newline=''));assert reader.fieldnames==HEADERS
 count=0
 for i,value in enumerate(reader):
  assert int(value['point'])==i and float(value['frequency_hz'])==i and value['gain']=='1' and value['gain_db']=='0'
  assert value['sample_status']==value['report_status']=='pass' and value['range_covered']=='true'
  assert value['below_minimum']==value['above_maximum']=='false' and None not in value
  count+=1
 assert count==100000
 checks.append({'label':'full-100000-sample-CSV','rows':count,'CSVBytes':large_csv.stat().st_size,'allIndicesAndCellsChecked':True})
 saved_sha=sha(output);run('gain-csv',sample,ohms,2,'saved-CSV-no-overwrite',output);assert sha(output)==saved_sha
 checks.append({'label':'saved-CSV-no-overwrite','preservedSHA256':saved_sha})
 for label,query,status,name in [('legacy-gamma',full,0,'pass'),('legacy-ohm',ohms,3,'fail')]:
  r=run('gain-check',sample,query,status,label);plain=json.loads(r.stdout)
  assert plain==frozen[name]['result'] and 'text' not in plain
  checks.append({'label':label,'sealed12PayloadPreserved':True})
 reviewed=run('gain-review',sample,'@'+str(frozen_dir/'receipt-fail.json'),0,'sealed12-receipt-still-reproduces')
 assert json.loads(reviewed.stdout)==json.loads((frozen_dir/'demo-review.json').read_text(encoding='utf-8'))
 checks.append({'label':'sealed12-receipt-still-reproduces','fullReviewPreserved':True})
 forbidden=json.loads((frozen_dir/'receipt-fail.json').read_text(encoding='utf-8'));forbidden['request']['command']='gain-csv'
 denied=save('forbidden-receipt-command.json',json.dumps(forbidden));r=run('gain-review',sample,'@'+str(denied),2,'receipt-does-not-expand-to-CSV')
 assert 'only gain-check' in r.stderr
 checks.append({'label':'receipt-does-not-expand-to-CSV','rejected':True})
 invalid=[('unknown-mode',{**full,'terminal_mode':'power'}),('mixed-terminal-units',{**full,'source_ohms':[50.,0.]}),
  ('missing-bound',{'start_hz':1e9,'end_hz':2e9}),('inverted-band',{**full,'end_hz':0.}),
  ('inverted-limits',{**full,'minimum_db':8.}),('missing-ohm-load',{'terminal_mode':'impedance','source_ohms':[50.,0.],**full}),
  ('bad-complex-shape',{**full,'source':[0.]}),('fixture-key-not-read',{**full,'left_file':str(work/'must-not-be-opened.txt')})]
 for label,query in invalid:
  r=run('gain-csv',sample,query,2,label)
  if label=='fixture-key-not-read':assert 'left_file' in r.stderr and 'ENOENT' not in r.stderr
  checks.append({'label':label,'rejected':True})
 non_ascii=work/'nonascii.s2p';non_ascii.write_bytes(b'!\xff\n'+sample.read_bytes());artifacts.append(non_ascii)
 r=run('gain-csv',non_ascii,full,2,'non-ASCII-input');assert 'ASCII' in r.stderr
 checks.append({'label':'non-ASCII-input','rejected':True})
 for target in ['js','wasm-gc']:
  demo=args.evidence.parent/('consumer-'+target+'.stdout.log')
  assert demo.read_text(encoding='utf-8').rstrip('\n')==output.read_text(encoding='ascii').rstrip('\n')
  checks.append({'label':'pure-MoonBit-consumer-'+target,'CSVMatchesActualOhmFile':True})
except Exception as exc:failure=exc
finally:
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'actualCLIProcesses':len(commands),'consumerChecks':len(checks),
  'commands':commands,'checks':checks,'oracle':'Python stdlib csv.DictReader, fixed five-state/bound truth cases and sealed12 scalar outputs; no RF oracle rerun.',
  'newManufacturerInputs':0,'newGTNumericalComparisons':0,'capacityRowsChecked':count if 'count' in globals() else 0,
  'artifacts':[{'path':str(p),'sha256':sha(p)} for p in artifacts],
  'sourceSHA256':{k:sha(ROOT/k) for k in ['gain_csv.mbt','gain_csv_test.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-gain-csv.py',
   'examples/gain_csv/main.mbt','gain.mbt','gain_impedance.mbt','gain_band.mbt']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['complete','failure','actualCLIProcesses','consumerChecks']},indent=2))
if failure:raise failure
