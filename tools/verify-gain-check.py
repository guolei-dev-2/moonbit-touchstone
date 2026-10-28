"""Independent sampled-GT report consumer and real CLI dispositions.

Synthetic GT values come from exact four-wave Fraction systems (Gamma or
physical Thevenin boundaries), with Decimal160 dB. Selection/decisions use
declarative Python masks, built-in extrema and hand-pinned status scenarios.
The oracle does not import the report implementation. Optional private NXP
input supplies a new aggregate reference from98 NumPy samples, not98 separate
GT value comparisons; only the report/extrema are retained, never the model.
"""
import argparse,hashlib,json,math,subprocess
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--vendor-input',type=Path);args=p.parse_args()
if args.evidence.exists():p.error('use a fresh receipt path')
host=subprocess.Popen(['node','tools/oracle-host.mjs'],cwd=ROOT,text=True,encoding='utf-8',stdin=subprocess.PIPE,stdout=subprocess.PIPE)
raw=[];checks=[];consumers=[];vendor=None
Z=(F(0),F(0));ONE=(F(1),F(0))
def q(z):return (F(complex(z).real),F(complex(z).imag))
def neg(a):return (-a[0],-a[1])
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def sub(a,b):return add(a,neg(b))
def mul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def norm(a):return a[0]**2+a[1]**2
def div(a,b):
 v=mul(a,(b[0],-b[1]));n=norm(b);return (v[0]/n,v[1]/n)
def exact_gain(m,refs,options):
 s11,s12,s21,s22=map(q,m)
 if options.get('terminal_mode','gamma')=='gamma':
  s=q(complex(*options.get('source',[0.,0.])));l=q(complex(*options.get('load',[0.,0.])))
  source_row=[ONE,Z,neg(s),Z,ONE];load_row=[Z,ONE,Z,neg(l),Z]
  factor=(1-norm(s))*(1-norm(l))
 else:
  s=q(complex(*options['source_ohms']));l=q(complex(*options['load_ohms']));rs,rl=map(q,refs)
  source_row=[add(rs,s),Z,sub(rs,s),Z,ONE];load_row=[Z,add(rl,l),Z,sub(rl,l),Z]
  factor=4*F(refs[0])*s[0]
 a=[[neg(s11),neg(s12),ONE,Z,Z],[neg(s21),neg(s22),Z,ONE,Z],source_row,load_row]
 for k in range(4):
  pivot=next((i for i in range(k,4) if a[i][k]!=Z),None)
  if pivot is None:return None
  a[k],a[pivot]=a[pivot],a[k];v=a[k][k];a[k]=[div(x,v) for x in a[k]]
  for i in range(4):
   if i!=k:
    v=a[i][k];a[i]=[sub(x,mul(v,y)) for x,y in zip(a[i],a[k])]
 return norm(a[3][4])*factor if options.get('terminal_mode','gamma')=='gamma' else (norm(a[3][4])-norm(a[1][4]))*factor
def logarithm(value):
 with localcontext() as c:
  c.prec=160;return float(10*(Decimal(value.numerator).ln()-Decimal(value.denominator).ln())/Decimal(10).ln())
def point(value,index,frequency):
 if value is None:return dict(point=index,frequency_hz=frequency,state='singular',gain=None,gain_db=None)
 if value==0:return dict(point=index,frequency_hz=frequency,state='zero',gain=0.,gain_db=None)
 assert value>0
 try:power=float(value)
 except OverflowError:power=math.inf
 state='overflow' if math.isinf(power) else 'underflow' if power==0 else 'finite'
 return dict(point=index,frequency_hz=frequency,state=state,gain=None if math.isinf(power) else power,gain_db=logarithm(value))
def expected_report(points,options):
 lo,hi=options['start_hz'],options['end_hz'];selected=[p for p in points if lo<=p['frequency_hz']<=hi]
 known=[p for p in selected if p['state']!='singular'];rank=lambda p:-math.inf if p['state']=='zero' else p['gain_db']
 below=[p for p in known if 'minimum_db' in options and rank(p)<options['minimum_db']]
 above=[p for p in known if 'maximum_db' in options and rank(p)>options['maximum_db']]
 covered=bool(points and points[0]['frequency_hz']<=lo and points[-1]['frequency_hz']>=hi)
 counts={state:sum(p['state']==state for p in selected) for state in ['finite','zero','singular','overflow','underflow']}
 status='fail' if below or above else 'inconclusive' if not covered or not selected or counts['singular'] else 'pass'
 reasons=set()
 if below:reasons.add('below_minimum')
 if above:reasons.add('above_maximum')
 if not covered:reasons.add('incomplete_range')
 if not selected:reasons.add('no_samples')
 if counts['singular']:reasons.add('singular_samples')
 if status=='pass':reasons.add('limits_met')
 return dict(scope='sampled_points_only',status=status,start_hz=lo,end_hz=hi,minimum_db=options.get('minimum_db'),maximum_db=options.get('maximum_db'),
  sample_count=len(selected),state_counts=counts,below_minimum_count=len(below),above_maximum_count=len(above),range_covered=covered,
  start_sampled=any(p['frequency_hz']==lo for p in points),end_sampled=any(p['frequency_hz']==hi for p in points),
  lowest=min(known,key=rank) if known else None,highest=max(known,key=rank) if known else None,reasons=sorted(reasons))
def verify_observation(actual,reference):
 if reference is None:assert actual is None;return
 assert actual is not None
 for key in ['point','frequency_hz','state']:assert actual[key]==reference[key],(key,actual,reference)
 for key in ['gain','gain_db']:
  a,b=actual.get(key),reference[key]
  if b is None:assert a is None
  else:assert isinstance(a,(int,float)) and abs(a-b)<=max(5e-324,abs(b)*3e-10,3e-11 if key=='gain_db' else 0.),(key,a,b)
def verify(result,reference,options,refs,label):
 assert result['status']==reference['status']
 mode=options.get('terminal_mode','gamma');assert result['terminal_mode']==mode and result['reference_ohms']==refs
 matching={key:options.get(key,[0.,0.]) for key in ['source','load']} if mode=='gamma' else {key:options[key] for key in ['source_ohms','load_ohms']}
 assert result['matching']==matching
 report=result['report']
 for key,value in reference.items():
  if key in ['lowest','highest']:verify_observation(report.get(key),value)
  elif key=='reasons':assert set(report[key])==set(value) and len(report[key])==len(value)
  else:assert report.get(key)==value,(label,key,report.get(key),value)
 checks.append({'label':label,'expectedStatus':reference['status'],'samples':reference['sample_count'],'reference':reference})
def file(matrices,refs):
 lines=['[Version] 2.1','# Hz S RI R 50','[Number of Ports] 2',f'[Number of Frequencies] {len(matrices)}','[Reference] '+' '.join(map(str,refs)),'[Two-Port Data Order] 12_21','[Network Data]']
 for i,m in enumerate(matrices):lines.append(str((i+1)*1e9)+' '+' '.join(format(v,'.17g') for z in m for v in [complex(z).real,complex(z).imag]))
 return '\n'.join(lines+['[End]',''])
def ask(matrices,options,label,status=None,reject=False,refs=None):
 refs=refs or [50.,50.];request={'text':file(matrices,refs),'options':{'command':'gain-check',**options}}
 host.stdin.write(json.dumps(request)+'\n');host.stdin.flush();line=host.stdout.readline();assert line,'bridge stopped'
 response=json.loads(line);raw.append({'label':label,'query':request,'response':response});assert response['ok']!=reject,(label,response)
 if reject:return
 points=[point(exact_gain(m,refs,options),i,(i+1)*1e9) for i,m in enumerate(matrices)];reference=expected_report(points,options)
 assert reference['status']==status,(label,reference,status)
 verify(response['result'],reference,options,refs,label)
 return reference
def cli(path,options,label,expected_exit,output=None):
 command=['node','tools/touchstone.mjs','gain-check',str(path),options if isinstance(options,str) else json.dumps(options)]
 if output:command.append(str(output))
 r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,encoding='utf-8');assert r.returncode==expected_exit,(label,r.stdout,r.stderr)
 item={'label':label,'command':command,'exitCode':r.returncode,'expectedExitCode':expected_exit,'stderr':r.stderr}
 consumers.append(item)
 if expected_exit==2:return None
 if output:
  assert r.stdout=='' and output.exists();item['savedReportSHA256']=hashlib.sha256(output.read_bytes()).hexdigest();return json.loads(output.read_text(encoding='utf-8'))
 return json.loads(r.stdout)
failure=None
try:
 base=[[.25,.125,2.,-.25],[.2,.1,1.5,-.2]];full={'start_hz':1e9,'end_hz':2e9}
 scenarios=[('gamma pass',{**full,'minimum_db':3.,'maximum_db':7.},'pass'),('gamma lower fail',{**full,'minimum_db':4.},'fail'),
 ('gamma upper fail',{**full,'maximum_db':6.},'fail'),('both bounds fail',{**full,'minimum_db':4.,'maximum_db':6.},'fail'),
 ('point interval',{'start_hz':1e9,'end_hz':1e9,'minimum_db':0.,'maximum_db':7.},'pass'),
 ('empty interior',{'start_hz':1.4e9,'end_hz':1.6e9,'minimum_db':0.},'inconclusive'),
 ('partial range',{**full,'start_hz':.5e9,'minimum_db':3.},'inconclusive'),
 ('known fail beats coverage',{**full,'start_hz':.5e9,'minimum_db':4.},'fail'),
 ('outside range',{'start_hz':3e9,'end_hz':4e9,'minimum_db':0.},'inconclusive')]
 ohms={'terminal_mode':'impedance','source_ohms':[100.,20.],'load_ohms':[25.,-10.]}
 scenarios += [('ohm pass',{**full,**ohms,'minimum_db':3.,'maximum_db':7.},'pass'),('ohm fail',{**full,**ohms,'minimum_db':4.,'maximum_db':7.},'fail')]
 for label,options,status in scenarios:ask(base,options,label,status)
 extremes=[[0.,0.,a,0.] for a in [0.,1e-200,1.,2.,1e200]]
 for label,options,status in [
  ('zero below finite lower',{'start_hz':1e9,'end_hz':5e9,'minimum_db':-5000.,'maximum_db':5000.},'fail'),
  ('positive extremes known',{'start_hz':2e9,'end_hz':5e9,'minimum_db':-5000.,'maximum_db':5000.},'pass'),
  ('zero meets upper',{'start_hz':1e9,'end_hz':1e9,'maximum_db':-5000.},'pass'),
  ('zero fails lower',{'start_hz':1e9,'end_hz':1e9,'minimum_db':-5000.},'fail'),
  ('overflow exceeds upper',{'start_hz':5e9,'end_hz':5e9,'maximum_db':3000.},'fail')]:ask(extremes,options,label,status)
 singular=[[0.,0.,1.,0.],[2.,0.,1.,0.],[0.,0.,2.,0.]]
 for label,options,status in [
  ('singular unknown',{'start_hz':1e9,'end_hz':3e9,'minimum_db':-2.,'source':[.5,0.]},'inconclusive'),
  ('known fail beats singular',{'start_hz':1e9,'end_hz':3e9,'minimum_db':0.,'source':[.5,0.]},'fail'),
  ('only singular',{'start_hz':2e9,'end_hz':2e9,'minimum_db':-2.,'source':[.5,0.]},'inconclusive'),
  ('ohm singular unknown',{'start_hz':1e9,'end_hz':3e9,'minimum_db':-2.,'terminal_mode':'impedance','source_ohms':[150.,0.],'load_ohms':[50.,0.]},'inconclusive')]:ask(singular,options,label,status)
 tied=[[0.,0.,a,0.] for a in [1.,1.,2.]]
 ask(tied,{'start_hz':1e9,'end_hz':2e9,'minimum_db':0.,'maximum_db':0.},'inclusive ties','pass')
 ask(tied,{'start_hz':1.25e9,'end_hz':2.75e9,'minimum_db':-1.},'single interior sample','pass')
 # Unequal port references with an independently equivalent physical match.
 ask(base,{**full,'terminal_mode':'impedance','source_ohms':[50.,0.],'load_ohms':[75.,0.],'minimum_db':3.,'maximum_db':7.},'unequal reference match','pass',refs=[50.,75.])
 valid={**full,'minimum_db':3.}
 invalid=[full,{'end_hz':2e9,'minimum_db':3.},{**valid,'end_hz':0.},{**valid,'start_hz':-1.},{**valid,'minimum_db':None},
  {**valid,'minimum_db':8.,'maximum_db':7.},{**full,'min_db':3.},{**valid,'terminal_mode':'ohm'},
  {**valid,'source_ohms':[50.,0.]},{**valid,'terminal_mode':'impedance','source_ohms':[50.,0.]},
  {**valid,**ohms,'source':[0.,0.]},{**valid,'source':[1.,0.]},{**valid,**ohms,'source_ohms':[0.,0.]},
  {**valid,'left_file':'ignored.json'},{**valid,'ports':.5},{**valid,'minimum_db':'3'}]
 for i,options in enumerate(invalid):ask(base,options,'invalid '+str(i),reject=True)
 sample=ROOT/'examples/power-gain.s2p'
 for name,options,status,argument,output in [
  ('file pass',{**full,'minimum_db':3.,'maximum_db':7.},'pass','@'+str(ROOT/'examples/gain-check-gamma.json'),None),
  ('file saved fail',{**full,**ohms,'minimum_db':4.,'maximum_db':7.},'fail','@'+str(ROOT/'examples/gain-check-ohms.json'),args.evidence.parent/(args.evidence.stem+'-cli-fail.json')),
  ('file incomplete',{'start_hz':1e9,'end_hz':3e9,'minimum_db':3.},'inconclusive',{'start_hz':1e9,'end_hz':3e9,'minimum_db':3.},None)]:
  reference=expected_report([point(exact_gain(m,[50.,50.],options),i,(i+1)*1e9) for i,m in enumerate(base)],options);assert reference['status']==status
  result=cli(sample,argument,name,{'pass':0,'fail':3,'inconclusive':4}[status],output);verify(result,reference,options,[50.,50.],name)
 cli(sample,{**full,'min_db':3.},'file invalid bound',2)
 cli(sample,{**full,**ohms,'minimum_db':3.,'source':[0.,0.]},'file mixed units',2)
 if args.vendor_input:
  import numpy as np,skrf
  digest=hashlib.sha256(args.vendor_input.read_bytes()).hexdigest();assert digest=='d4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95'
  model=skrf.Network(str(args.vendor_input));assert len(model.f)==98
  amplitude=np.abs(model.s[:,1,0]);decibels=20*np.log10(amplitude)
  points=[dict(point=i,frequency_hz=float(f),state='finite',gain=float(a*a),gain_db=float(d)) if a else dict(point=i,frequency_hz=float(f),state='zero',gain=0.,gain_db=None) for i,(f,a,d) in enumerate(zip(model.f,amplitude,decibels))]
  options={'start_hz':float(model.f[0]),'end_hz':float(model.f[-1]),'minimum_db':2.,'maximum_db':30.}
  reference=expected_report(points,options);result=cli(args.vendor_input,options,'NXP aggregate report',{'pass':0,'fail':3,'inconclusive':4}[reference['status']])
  verify(result,reference,options,[50.,50.],'NXP aggregate report')
  vendor={'sha256':digest,'bytes':args.vendor_input.stat().st_size,'referenceSamplesClassified':98,'individualGTComparisons':0,'skrfVersion':skrf.__version__,'numpyVersion':np.__version__,
   'policy':'Only aggregate report, counts and two extrema retained; no original model, S matrix or full GT export.'}
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'requests':len(raw),'reportChecks':len(checks),'checks':checks,'raw':raw,'fileConsumers':consumers,'vendor':vendor,
  'oracle':'Exact Fraction four-wave power with Decimal160 dB; declarative masks/builtin extrema and hand-pinned status table; NumPy98-sample aggregate NXP reference only',
  'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['gain_band.mbt','gain_band_test.mbt','gain.mbt','gain_impedance.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-gain-check.py','examples/gain-check-gamma.json','examples/gain-check-ohms.json','examples/gain_check/main.mbt','examples/gain_check/moon.pkg']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','requests','reportChecks']},indent=2))
if failure:raise failure
