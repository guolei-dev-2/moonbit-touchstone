"""Physical-ohm GT consumer with independent exact Thevenin wave equations.

No Gamma conversion, homogeneous determinant or expanded polynomial is used by
the primary oracle. b=S*a and physical source/load voltage-current boundaries
are solved by Fraction complex Gaussian elimination; Decimal160 gives dB.
Optional pinned NXP file remains private; only three scalar comparisons are
recorded, not its model or complete outputs. Frozen09 values supply just a
small old Gamma CLI routing control, not a rerun of an archived suite.
"""
import argparse,hashlib,json,math,random,subprocess
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--vendor-input',type=Path);p.add_argument('--skip-gamma-controls',action='store_true');args=p.parse_args()
if args.evidence.exists():p.error('use fresh receipt path')
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
def gain(m,refs,source,load):
 s11,s12,s21,s22=map(q,m);s,l=q(source),q(load);rs,rl=map(q,refs)
 # Unknowns a1,a2,b1,b2. Source RHS=Vs*sqrt(Rs)=1, so available
 # source power=1/(4*Rs*Re(Zs)). Load power=|b2|²-|a2|².
 a=[[neg(s11),neg(s12),ONE,Z,Z],[neg(s21),neg(s22),Z,ONE,Z],
    [add(rs,s),Z,sub(rs,s),Z,ONE],[Z,add(rl,l),Z,sub(rl,l),Z]]
 for k in range(4):
  pivot=next((i for i in range(k,4) if a[i][k]!=Z),None)
  if pivot is None:return None
  a[k],a[pivot]=a[pivot],a[k];v=a[k][k];a[k]=[div(x,v) for x in a[k]]
  for i in range(4):
   if i!=k:
    v=a[i][k];a[i]=[sub(x,mul(v,y)) for x,y in zip(a[i],a[k])]
 return (norm(a[3][4])-norm(a[1][4]))*4*F(refs[0])*F(complex(source).real)
def db(value):
 with localcontext() as c:
  c.prec=160;return float(10*(Decimal(value.numerator).ln()-Decimal(value.denominator).ln())/Decimal(10).ln())
def file(matrices,refs):
 lines=['[Version] 2.1','# Hz S RI R 50','[Number of Ports] 2',f'[Number of Frequencies] {len(matrices)}','[Reference] '+' '.join(format(v,'.17g') for v in refs),'[Two-Port Data Order] 12_21','[Network Data]']
 for i,m in enumerate(matrices):lines.append(str((i+1)*1e9)+' '+' '.join(format(v,'.17g') for z in m for v in [complex(z).real,complex(z).imag]))
 return '\n'.join(lines+['[End]',''])
def opts(source,load):return {'source_ohms':[complex(source).real,complex(source).imag],'load_ohms':[complex(load).real,complex(load).imag]}
def check(point,m,refs,source,load,label):
 expected=gain(m,refs,source,load)
 if expected is None:
  assert point['state']=='singular' and point.get('gain') is None and point.get('gain_db') is None,(label,point)
  checks.append({'label':label,'state':'singular'});return
 if expected==0:
  assert point['state']=='zero' and point['gain']==0 and point.get('gain_db') is None,(label,point)
  checks.append({'label':label,'state':'zero'});return
 assert expected>0
 try:power=float(expected)
 except OverflowError:power=math.inf
 state='overflow' if math.isinf(power) else 'underflow' if power==0 else 'finite'
 assert point['state']==state,(label,point,state)
 if state=='overflow':assert point.get('gain') is None
 elif power==0:assert point['gain']==0
 else:assert abs(point['gain']-power)<=max(5e-324,abs(power)*3e-11),(label,point,power)
 logarithm=db(expected);assert abs(point['gain_db']-logarithm)<=max(3e-11,abs(logarithm)*3e-12),(label,point,logarithm)
 checks.append({'label':label,'state':state,'referenceGain':None if math.isinf(power) else power,'actualGain':point.get('gain'),
  'referenceDB':logarithm,'actualDB':point['gain_db'],'exactRationalSHA256':hashlib.sha256(str(expected).encode()).hexdigest()})
def ask(matrices,refs,options,label,reject=False):
 request={'text':file(matrices,refs),'options':{'command':'transducer-gain-impedance',**options}}
 host.stdin.write(json.dumps(request)+'\n');host.stdin.flush();line=host.stdout.readline();assert line,'bridge stopped'
 response=json.loads(line);raw.append({'label':label,'query':request,'response':response});assert response['ok']!=reject,(label,response)
 return response.get('result')
def cli(command,path,options,label,expected_exit=0):
 query=['node','tools/touchstone.mjs',command,str(path),options if isinstance(options,str) else json.dumps(options)]
 r=subprocess.run(query,cwd=ROOT,text=True,capture_output=True,encoding='utf-8');assert r.returncode==expected_exit,(label,r.stdout,r.stderr)
 consumers.append({'label':label,'command':query,'exitCode':r.returncode,'expectedExitCode':expected_exit,'stderr':r.stderr})
 return json.loads(r.stdout) if r.returncode==0 else None
failure=None
try:
 wire=[0.,1.,1.,0.];bilateral=[.25,.125,2.,-.25];oneway=[0.,0.,1.,0.];tiny=5e-324
 cases=[('matched unequal',bilateral,[50.,75.],50.,75.),('rational unequal',bilateral,[50.,75.],150.,125.),
 ('ordinary complex',[.25+.1j,.125-.05j,2-.2j,-.25+.02j],[50.,75.],100+20j,25-10j),
 ('wire huge',wire,[50.,50.],1e308,1e308),('wire minimum',wire,[50.,50.],tiny,tiny),
 ('wire conjugate',wire,[50.,50.],complex(tiny,1e308),complex(tiny,-1e308)),
 ('huge network reference',wire,[1e308,1e308],1e308,1e308),('tiny network reference',wire,[tiny,tiny],tiny,tiny),
 ('unlike network references',wire,[tiny,1e308],tiny,1e308),('reverse unlike references',wire,[1e308,tiny],1e308,tiny),
 ('overflow amplitude',[0.,0.,1e200,0.],[50.,50.],50.,50.),('underflow amplitude',[0.,0.,1e-200,0.],[50.,50.],50.,50.),
 ('positive large source',oneway,[50.,50.],1e308,50.),('positive tiny source',oneway,[50.,50.],1e-308,50.),
 ('zero short',oneway,[50.,50.],50.,0.),('zero reactive',oneway,[50.,50.],50.,50j),
 ('positive source pole',[2.,0.,1.,0.],[50.,50.],150.,50.),('zero singular priority',[0.,0.,1.,-1.],[50.,50.],50.,0.),
 ('matched rank one large',[1e100,1e100,1e100,1e100],[50.,50.],50.,50.),
 ('matched rank one overflow',[1e200,1e200,1e200,1e200],[50.,50.],50.,50.)]
 rng=random.Random(20261028)
 for i in range(24):
  z=lambda limit:complex(rng.randint(-limit,limit)/16,rng.randint(-limit,limit)/16)
  cases.append((f'ordinary physical wave {i}',[z(6),z(4),z(32),z(6)],[50.,75.],complex(2.**rng.randint(-8,8),rng.randint(-100,100)/2),complex(2.**rng.randint(-8,8),rng.randint(-100,100)/2)))
 for label,m,refs,source,load in cases:
  points=ask([m],refs,opts(source,load),label);assert len(points)==1 and points[0]['frequency_hz']==1e9
  check(points[0],m,refs,source,load,label)
 # Multi-frequency report with real ohm terminals, retaining zero/pole/finite.
 mats=[oneway,[2.,0.,1.,0.],bilateral];points=ask(mats,[50.,50.],opts(150.,50.),'batched report');assert len(points)==3
 for i,(m,point) in enumerate(zip(mats,points)):
  assert point['frequency_hz']==(i+1)*1e9;check(point,m,[50.,50.],150.,50.,'batch '+str(i))
 for options in [{},{'source_ohms':[50.,0.]},{'source':[0.,0.],'load':[0.,0.]},
  {**opts(50.,50.),'left_file':'unknown.txt'},{**opts(50.,50.),'source':[0.,0.]},
  {**opts(50.,50.),'source_ohms':[50.]},{**opts(50.,50.),'load_ohms':None},opts(0.,50.),opts(-1.,50.),opts(50.,-tiny)]:
  ask([oneway],[50.,50.],options,'invalid input',reject=True)
 sample=ROOT/'examples/power-gain.s2p'
 points=cli('transducer-gain-impedance',sample,'@'+str(ROOT/'examples/power-gain-ohms.json'),'physical file')
 assert len(points)==2
 for i,m in enumerate([bilateral,[.2,.1,1.5,-.2]]):check(points[i],m,[50.,50.],100+20j,25-10j,'physical file '+str(i))
 for options in [{},{'source':[0.,0.],'load':[0.,0.]},opts(0.,50.),{**opts(50.,50.),'left_file':str(ROOT/'examples/power-gain-ohms.json')}]:
  cli('transducer-gain-impedance',sample,options,'physical CLI rejection',expected_exit=2)
 # A few old Gamma-routing controls against immutable09 independent values.
 if not args.skip_gamma_controls:
  old=json.loads((ROOT/'evidence/matching-repair-20261028/independent-first.json').read_text(encoding='utf-8'))
  expected=[next(x for x in old['checks'] if x['label']=='synthetic file '+str(i)) for i in range(2)]
  points=cli('transducer-gain',sample,'@'+str(ROOT/'examples/power-gain-near-circle.json'),'preserved09 Gamma file')
  for point,reference in zip(points,expected):assert abs(point['gain']-reference['gain'])<=abs(reference['gain'])*3e-13 and point['state']==reference['state']
  points=cli('transducer-gain',sample,{},'preserved matched Gamma file');assert [x['gain'] for x in points]==[4.,2.25]
  cli('transducer-gain',sample,{'source':[1.,0.]},'preserved invalid Gamma',expected_exit=2)
  cli('transducer-gain',sample,{'left_file':str(ROOT/'examples/power-gain-ohms.json')},'preserved Gamma fixture rejection',expected_exit=2)
 if args.vendor_input:
  import skrf
  actual=hashlib.sha256(args.vendor_input.read_bytes()).hexdigest();assert actual=='d4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95'
  model=skrf.Network(str(args.vendor_input));assert len(model.f)==98
  points=cli('transducer-gain-impedance',args.vendor_input,opts(100+20j,25-10j),'NXP selected physical-terminal query');assert len(points)==98
  for i in [0,49,97]:
   assert points[i]['frequency_hz']==float(model.f[i]);check(points[i],model.s[i].flatten(),[float(x.real) for x in model.z0[i]],100+20j,25-10j,'NXP selected '+str(i))
  vendor={'sha256':actual,'bytes':args.vendor_input.stat().st_size,'returnedPoints':98,'validatedIndices':[0,49,97],'skrfVersion':skrf.__version__,
   'policy':'No original model, S matrix or complete output stored; three selected scalar gain comparisons only.'}
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 result={'complete':failure is None,'failure':repr(failure) if failure else None,'requests':len(raw),'pointChecks':len(checks),'checks':checks,'raw':raw,'fileConsumers':consumers,'vendor':vendor,
  'gammaControlsSkipped':args.skip_gamma_controls,'oracle':'Fraction exact four-wave solve with physical Thevenin voltage/current terminal conditions; Decimal160 dB. No Gamma or polynomial oracle.',
  'primaryReferences':['https://qucs.sourceforge.net/tech/node6.html','https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html'],
  'sourceSHA256':{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['gain.mbt','gain_impedance.mbt','gain_impedance_test.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-gain-impedance.py','examples/power-gain-ohms.json','examples/power_gain_ohms/main.mbt','examples/power_gain_ohms/moon.pkg']}}
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','requests','pointChecks']},indent=2))
if failure:raise failure
