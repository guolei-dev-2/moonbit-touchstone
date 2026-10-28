"""Independent transducer consumer: solve incident/reflected wave equations.

Fraction complex Gaussian elimination of FOUR wave unknowns is the primary
oracle, not the implementation's expanded determinant/scaled power algorithm.
NumPy independently solves ordinary cases. Synthetic inputs only; no RF vendor
models, historical suite, upstream source code, or self roundtrip as sole oracle.
"""
import argparse,hashlib,json,math,random,subprocess
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
if args.evidence.exists():p.error('use fresh receipt path')
host=subprocess.Popen(['node','tools/oracle-host.mjs'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf-8')
raw=[];checks=[];consumers=[]
Z=(F(0),F(0));ONE=(F(1),F(0))
def q(z):return (F(z.real),F(z.imag))
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def neg(a):return (-a[0],-a[1])
def sub(a,b):return add(a,neg(b))
def mul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
def norm(a):return a[0]*a[0]+a[1]*a[1]
def div(a,b):
 n=norm(b);v=mul(a,(b[0],-b[1]));return (v[0]/n,v[1]/n)
def equations(m,gs,gl):
 s11,s12,s21,s22=[q(complex(v)) for v in m];gs,gl=q(complex(gs)),q(complex(gl))
 # b1=S11*a1+S12*a2, b2=S21*a1+S22*a2;
 # a1=1+Gs*b1, a2=Gl*b2. Generator wave is 1, not available power 1.
 return [[neg(s11),neg(s12),ONE,Z],[neg(s21),neg(s22),Z,ONE],[ONE,Z,neg(gs),Z],[Z,ONE,Z,neg(gl)]]
def exact(m,gs,gl):
 a=[row+[b] for row,b in zip(equations(m,gs,gl),[Z,Z,ONE,Z])]
 for k in range(4):
  pivot=next((j for j in range(k,4) if a[j][k]!=Z),None)
  if pivot is None:return None
  a[k],a[pivot]=a[pivot],a[k];v=a[k][k];a[k]=[div(x,v) for x in a[k]]
  for j in range(4):
   if j!=k:
    v=a[j][k];a[j]=[sub(x,mul(v,y)) for x,y in zip(a[j],a[k])]
 return norm(a[3][4])*(1-norm(q(complex(gs))))*(1-norm(q(complex(gl))))
def log_db(value):
 with localcontext() as c:
  c.prec=160
  return float(10*(Decimal(value.numerator).ln()-Decimal(value.denominator).ln())/Decimal(10).ln())
def record_text(matrices,parameter='S',refs=(50.,75.)):
 lines=['[Version] 2.1',f'# Hz {parameter} RI R 50','[Number of Ports] 2',f'[Number of Frequencies] {len(matrices)}','[Reference] '+' '.join(map(str,refs)),'[Two-Port Data Order] 12_21','[Network Data]']
 for i,m in enumerate(matrices):lines.append(str((i+1)*1e9)+' '+' '.join(format(v,'.17g') for z in m for v in [complex(z).real,complex(z).imag]))
 return '\n'.join(lines+['[End]',''])
def ask(text,options=None,reject=False):
 request={'text':text,'options':{'command':'transducer-gain',**(options or {})}}
 host.stdin.write(json.dumps(request)+'\n');host.stdin.flush();line=host.stdout.readline();assert line,'bridge stopped'
 response=json.loads(line);raw.append({'query':request,'response':response});assert response['ok']!=reject,response
 return response.get('result')
def near(a,b,rtol=2e-12,atol=2e-323):assert a is not None and abs(a-b)<=max(atol,abs(b)*rtol),(a,b)
def check(point,m,gs,gl,label,numpy=False):
 value=exact(m,gs,gl)
 if value is None:
  assert point['state']=='singular' and point.get('gain') is None and point.get('gain_db') is None,(label,point)
  checks.append({'label':label,'state':'singular'});return
 if value==0:
  assert point['state']=='zero' and point['gain']==0 and point.get('gain_db') is None,(label,point)
  checks.append({'label':label,'state':'zero'});return
 assert value>0
 try:linear=float(value)
 except OverflowError:linear=math.inf
 state='overflow' if math.isinf(linear) else 'underflow' if linear==0 else 'finite'
 assert point['state']==state,(label,point,state)
 if state=='overflow':assert point.get('gain') is None
 else:near(point['gain'],linear)
 db=log_db(value);near(point['gain_db'],db,rtol=3e-13,atol=3e-12)
 if numpy:
  a=np.array([[complex(float(x),float(y)) for x,y in row] for row in equations(m,gs,gl)])
  waves=np.linalg.solve(a,np.array([0.,0.,1.,0.],dtype=complex))
  ref=abs(waves[3])**2*(1-abs(gs)**2)*(1-abs(gl)**2);near(ref,linear)
 checks.append({'label':label,'state':state,'gain':None if math.isinf(linear) else linear,'gain_db':db,
  'exactRationalSHA256':hashlib.sha256(str(value).encode()).hexdigest(),'numpyWaveSolve':numpy})
failure=None
try:
 cases=[
 ('matched',[.25,.125,2.,-.25],0.,0.),('bilateral rational',[.25,.125,2.,-.25],.5,.25),
 ('quarter-wave',[0.,-1j,-1j,0.],.5j,-.5j),('blocked',[0.,0.,0.,0.],.2,.3),
 ('load open',[.1,.2,.8,.3],.2,1.),('load short',[.1,.2,.8,.3],.2,-1.),('load imaginary',[.1,.2,.8,.3],.2,1j),
 ('feedback pole',[2.,0.,1.,0.],.5,0.),('load pole',[0.,0.,1.,1.],0.,1.),('blocked pole',[2.,0.,0.,0.],.5,0.),
 ('small finite',[0.,0.,2.**-500,0.],0.,0.),('subnormal finite',[0.,0.,2.**-530,0.],0.,0.),
 ('positive underflow',[0.,0.,1e-200,0.],0.,0.),('minimum subnormal amplitude',[0.,0.,5e-324,0.],0.,0.),
 ('positive overflow',[0.,0.,1e200,0.],0.,0.),('largest finite amplitude',[0.,0.,float.fromhex('0x1.fffffffffffffp1023'),0.],0.,0.),
 ('finite despite squared overflow',[1e200,0.,1e200,0.],.5,0.),('large determinant products',[1e308,.1,1e200,1e308],.5,.25),
 ('rank one same signs',[1e200,1e200,1e200,1e200],.5,.5),('rank one opposite signs',[1e200,1e200,-1e200,-1e200],.5,.5),
 ('mixed transfer scales',[0.,1e200,1e-200,0.],.5,.5),('source near unit circle',[0.,1.,1.,0.],math.nextafter(1.,0.),0.),
 ('load near unit circle',[0.,1.,1.,0.],0.,math.nextafter(1.,0.))]
 rng=random.Random(20261028)
 for i in range(32):
  z=lambda limit:complex(rng.randint(-limit,limit)/16,rng.randint(-limit,limit)/16)
  cases.append((f'complex wave system {i}',[z(6),z(4),z(32),z(6)],z(4),z(8)))
 for i,(label,m,gs,gl) in enumerate(cases):
  points=ask(record_text([m]),{'source':[complex(gs).real,complex(gs).imag],'load':[complex(gl).real,complex(gl).imag]});assert len(points)==1
  assert points[0]['frequency_hz']==1e9
  check(points[0],m,gs,gl,label,numpy=i>=23)
 # Batched reports preserve every sample, including zero/pole/ordinary states.
 matrices=[[0.,0.,0.,0.],[2.,0.,1.,0.],[.25,.125,2.,-.25]]
 points=ask(record_text(matrices),{'source':[.5,0.],'load':[0.,0.]});assert len(points)==3
 for i,(point,m) in enumerate(zip(points,matrices)):
  assert point['frequency_hz']==(i+1)*1e9;check(point,m,.5,0.,'batch '+str(i))
 # Independent NumPy voltage/current conversions, same real port references.
 m=np.array([[.1,.02],[.5,-.1]],dtype=complex);r=np.diag(np.sqrt([50.,75.]))
 z=r@(np.eye(2)+m)@np.linalg.inv(np.eye(2)-m)@r;y=np.linalg.inv(z)
 h=np.array([[z[0,0]-z[0,1]*z[1,0]/z[1,1],z[0,1]/z[1,1]],[-z[1,0]/z[1,1],1/z[1,1]]]);g=np.linalg.inv(h)
 for kind,mat in [('Z',z),('Y',y),('H',h),('G',g)]:
  points=ask(record_text([mat.flatten()],parameter=kind),{'source':[.2,0.],'load':[-.3,0.]})
  check(points[0],m.flatten(),.2,-.3,'independent '+kind+' physical units')
 invalid=[{'source':[1.,0.]},{'source':[-1.,0.]},{'source':[0.,1.]},{'source':[.9,.9]},{'load':[1.001,0.]},
  {'load':[0.,-1.001]},{'source':[0.]},{'source':None},{'load':['bad',0.]},{'soruce':[0.,0.]}]
 for options in invalid:ask(record_text([[0.,0.,1.,0.]]),options,reject=True)
 ask('# Hz S RI R 50\n1 0 0\n',{'ports':1},reject=True)
 # Actual file CLI, using the delivered options file and default matched case.
 sample=ROOT/'examples/power-gain.s2p';options=ROOT/'examples/power-gain-options.json'
 for opts,gs,gl in [([],0.,0.),(['@'+str(options)],.5,.25)]:
  command=['node','tools/touchstone.mjs','transducer-gain',str(sample),*opts]
  r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);assert r.returncode==0,r.stderr
  points=json.loads(r.stdout);assert len(points)==2
  for i,m in enumerate([[.25,.125,2.,-.25],[.2,.1,1.5,-.2]]):check(points[i],m,gs,gl,'file CLI '+str(i))
  consumers.append({'command':command,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 for opts in [{'source':[1.,0.]},{'soruce':[0.,0.]},{'left_file':str(options)}]:
  command=['node','tools/touchstone.mjs','transducer-gain',str(sample),json.dumps(opts)]
  r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);assert r.returncode==2 and r.stderr.strip()
  consumers.append({'command':command,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'requests':len(raw),'pointChecks':len(checks),'checks':checks,'raw':raw,'fileConsumers':consumers,
  'oracle':'Fraction exact complex four-wave Gaussian elimination; NumPy four-wave solve for 32 fixed ordinary complex cases; Decimal160 log ratio',
  'numpyVersion':np.__version__,'primaryDefinition':'https://qucs.sourceforge.net/tech/node6.html',
  'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['gain.mbt','gain_test.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-gain.py','examples/power_gain/main.mbt','examples/power_gain/moon.pkg','examples/power-gain.s2p','examples/power-gain-options.json']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','requests','pointChecks']},indent=2))
if failure:raise failure
