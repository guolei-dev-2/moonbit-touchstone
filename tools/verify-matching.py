"""Round09: exact matching-domain boundaries and actual file GT consumers.

Fraction operates on parsed binary64 components; it never computes hypot or
copies the production square splitting/expansion. Four-wave exact elimination
is the gain oracle. Optional pinned NXP input stays outside the project; only
three selected scalar results/errors per query are recorded, no raw model or
complete 98-sample export. This does not rerun historical vendor validations.
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
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def neg(a):return (-a[0],-a[1])
def sub(a,b):return add(a,neg(b))
def mul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def norm(a):return a[0]**2+a[1]**2
def div(a,b):
 v=mul(a,(b[0],-b[1]));n=norm(b);return (v[0]/n,v[1]/n)
def margin(g):return 1-norm(q(g))
def gain(m,gs,gl):
 s11,s12,s21,s22=map(q,m);s,l=q(gs),q(gl)
 a=[[neg(s11),neg(s12),ONE,Z,Z],[neg(s21),neg(s22),Z,ONE,Z],[ONE,Z,neg(s),Z,ONE],[Z,ONE,Z,neg(l),Z]]
 for k in range(4):
  pivot=next((i for i in range(k,4) if a[i][k]!=Z),None)
  if pivot is None:return None
  a[k],a[pivot]=a[pivot],a[k];v=a[k][k];a[k]=[div(x,v) for x in a[k]]
  for i in range(4):
   if i!=k:
    v=a[i][k];a[i]=[sub(x,mul(v,y)) for x,y in zip(a[i],a[k])]
 return norm(a[3][4])*margin(gs)*margin(gl)
def db(value):
 with localcontext() as c:
  c.prec=160;return float(10*(Decimal(value.numerator).ln()-Decimal(value.denominator).ln())/Decimal(10).ln())
def text(m):
 return '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 1\n[Reference] 50 75\n[Two-Port Data Order] 12_21\n[Network Data]\n1 '+' '.join(format(v,'.17g') for z in m for v in [complex(z).real,complex(z).imag])+'\n[End]\n'
def options(gs,gl):return {'source':[complex(gs).real,complex(gs).imag],'load':[complex(gl).real,complex(gl).imag]}
def check(point,m,gs,gl,label,rtol=3e-13):
 value=gain(m,gs,gl)
 if value is None:
  assert point['state']=='singular' and point.get('gain') is None and point.get('gain_db') is None
  checks.append({'label':label,'state':'singular'});return
 if not value:
  assert point['state']=='zero' and point['gain']==0 and point.get('gain_db') is None
  checks.append({'label':label,'state':'zero'});return
 assert value>0
 try:power=float(value)
 except OverflowError:power=math.inf
 state='overflow' if math.isinf(power) else 'underflow' if power==0 else 'finite'
 assert point['state']==state,(label,point,state)
 if state=='overflow':assert point.get('gain') is None
 elif power==0:assert point['gain']==0
 else:assert abs(point['gain']-power)<=max(5e-324,abs(power)*rtol),(label,point,power)
 logarithm=db(value);assert abs(point['gain_db']-logarithm)<=max(3e-12,abs(logarithm)*rtol),(label,point,logarithm)
 checks.append({'label':label,'state':state,'gain':None if math.isinf(power) else power,'gain_db':logarithm,
  'exactSourceMargin':str(margin(gs)),'exactLoadMargin':str(margin(gl)),
  'exactRationalSHA256':hashlib.sha256(str(value).encode()).hexdigest()})
def ask(m,gs,gl,label):
 request={'text':text(m),'options':{'command':'transducer-gain',**options(gs,gl)}}
 host.stdin.write(json.dumps(request)+'\n');host.stdin.flush();line=host.stdout.readline();assert line,'bridge stopped'
 response=json.loads(line);raw.append({'label':label,'query':request,'response':response})
 valid=margin(gs)>0 and margin(gl)>=0
 assert response['ok']==valid,(label,response,valid)
 if valid:
  points=response['result'];assert len(points)==1 and points[0]['frequency_hz']==1
  check(points[0],m,gs,gl,label)
def cli(path,opts):
 command=['node','tools/touchstone.mjs','transducer-gain',str(path),opts if isinstance(opts,str) else json.dumps(opts)]
 r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,encoding='utf-8');assert r.returncode==0,r.stderr
 return command,json.loads(r.stdout),r
failure=None
try:
 unit=[0.,0.,1.,0.];coupled=[.25+.1j,.125-.05j,2.-.2j,-.25+.02j]
 for x in [.6,.75,.9999999999999999,math.sqrt(.5)]:
  with localcontext() as c:
   c.prec=160;y=float((Decimal(1)-Decimal.from_float(x)**2).sqrt())
  for yvalue in [math.nextafter(y,0.),y,math.nextafter(y,math.inf)]:
   g=complex(x,yvalue)
   for label,gs,gl in [('source',g,0.),('load',0.,g),('both',g,g)]:ask(unit,gs,gl,f'circle {x!r} {yvalue!r} '+label)
 near=complex(.9999999999999999,1.4901161193847655e-8)
 for g in [near,-near,complex(near.imag,near.real),complex(-near.imag,near.real)]:
  ask(coupled,g,.2-.1j,'coupled near source '+repr(g))
  ask(coupled,.2+.1j,g,'coupled near load '+repr(g))
 for g in [complex(1.,5e-324),complex(-1.,1e-200),complex(1e-200,1.),complex(-5e-324,-1.)]:
  ask(unit,0.,g,'tiny active load '+repr(g));ask(unit,g,0.,'tiny active source '+repr(g))
 for g in [1.,-1.,1j,-1j]:
  ask(unit,0.,g,'axis load '+repr(g));ask(unit,g,0.,'axis source '+repr(g))
 for g in [0.,.2+.1j]:ask(coupled,g,g,'ordinary matching '+repr(g))
 for amplitude in [1e200,1e-200]:
  ask([0.,0.,amplitude,0.],near,0.,'large/small transfer source '+repr(amplitude))
  ask([0.,0.,amplitude,0.],near,near,'large/small transfer both '+repr(amplitude))
 # Existing synthetic S2P, new near-circle options file through the real CLI.
 command,points,r=cli(ROOT/'examples/power-gain.s2p','@'+str(ROOT/'examples/power-gain-near-circle.json'))
 assert len(points)==2
 for i,m in enumerate([[.25,.125,2.,-.25],[.2,.1,1.5,-.2]]):check(points[i],m,near,0.,'synthetic file '+str(i))
 consumers.append({'command':command,'exitCode':r.returncode,'returnedPoints':2,'validatedPoints':2,'stderr':r.stderr})
 if args.vendor_input:
  import skrf
  expected='d4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95'
  actual=hashlib.sha256(args.vendor_input.read_bytes()).hexdigest();assert actual==expected,'NXP input identity drift'
  model=skrf.Network(str(args.vendor_input));assert len(model.f)==98
  vendor={'sha256':actual,'bytes':args.vendor_input.stat().st_size,'modelPoints':98,'checkedIndices':[0,49,97],'skrfVersion':skrf.__version__,
   'dataPolicy':'Original model and complete scalar exports omitted; only three selected gain references per query.'}
  for gs,gl in [(near,0.),(near,near)]:
   command,points,r=cli(args.vendor_input,options(gs,gl));assert len(points)==98
   for i in vendor['checkedIndices']:
    assert points[i]['frequency_hz']==float(model.f[i]);check(points[i],model.s[i].flatten(),gs,gl,'NXP selected '+str(i),rtol=3e-11)
   consumers.append({'command':command,'exitCode':r.returncode,'returnedPoints':98,'validatedPoints':3,'stderr':r.stderr})
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'requests':len(raw),'pointChecks':len(checks),'checks':checks,'raw':raw,
  'fileConsumers':consumers,'vendor':vendor,'oracle':'Fraction exact binary64 domain + four-wave Gaussian elimination; Decimal160 logarithm; independent scikit-rf parser for selected NXP values',
  'primaryReferences':['https://qucs.sourceforge.net/tech/node6.html','https://www.cs.cmu.edu/~quake/robust.html'],
  'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['gain.mbt','matching_test.mbt','tools/verify-matching.py','tools/touchstone.mjs','cmd/bridge/main.mbt','examples/power-gain-near-circle.json']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','requests','pointChecks']},indent=2))
if failure:raise failure
