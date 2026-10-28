"""Independent high-precision RF limits, exact loads and low-noise consumer.

800-digit Decimal evaluates the ORIGINAL MAG expression (including subtraction)
as a reference, not the implementation's rationalized expression. Fraction
evaluates complex impedance/load feedback exactly. scikit-rf supplies independent
noise covariances and interpolation. Synthetic inputs only; fresh receipt path.
"""
import argparse,hashlib,inspect,json,math,subprocess,warnings
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import skrf as rf
from skrf.constants import K_BOLTZMANN,T0
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
if args.evidence.exists():p.error('use a fresh receipt')
host=subprocess.Popen(['node','tools/oracle-host.mjs'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf-8')
raw=[];checks=[];disagreements=[]
def text(s,refs=(50.,50.),noise=None):
 n=s.shape[1]
 # Noise Gamma is referenced by option-line R, independently of [Reference].
 lines=['[Version] 2.1',f'# Hz S RI R {refs[0]:.17g}',f'[Number of Ports] {n}',f'[Number of Frequencies] {len(s)}',
 '[Reference] '+' '.join(format(v,'.17g') for v in refs)]
 if n==2:lines.append('[Two-Port Data Order] 12_21')
 if noise is not None:lines.append('[Number of Noise Frequencies] 2')
 lines+=['[Network Data]']
 for f,m in enumerate(s,1):lines+=[' '.join([str(f)]+[format(v,'.17g') for z in m.ravel() for v in [z.real,z.imag]])]
 if noise is not None:
  lines+=['[Noise Data]']
  for f,rn in enumerate(noise,1):lines.append(f'{f} 0 0 0 {rn:.17g}')
 return '\n'.join(lines+['[End]'])+'\n'
def ask(t,command,reject=False,left='',right='',**kw):
 q=dict(text=t,left=left,right=right,options=dict(command=command,**kw));host.stdin.write(json.dumps(q)+'\n');host.stdin.flush()
 line=host.stdout.readline();assert line,'bridge stopped';r=json.loads(line);raw.append(dict(query=q,response=r));assert r['ok']!=reject,r
 return r.get('result')
def close(got,want,label,rtol=1e-10,atol=1e-13):
 np.testing.assert_allclose(got,want,rtol=rtol,atol=atol,err_msg=label)
 checks.append(dict(label=label,maxAbsoluteError=float(np.max(np.abs(np.asarray(got)-want)))))
def stability_oracle(m):
 # Decimal from exact binary64 inputs; direct original K and K-sqrt(K^2-1).
 with localcontext() as ctx:
  ctx.prec=800
  z=[(D.from_float(z.real),D.from_float(z.imag)) for z in m.ravel()]
  def cmul(a,b):return a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]
  def abssq(a):return a[0]*a[0]+a[1]*a[1]
  r=cmul(z[0],z[3]);t=cmul(z[1],z[2]);delta=(r[0]-t[0],r[1]-t[1])
  c=abssq(t).sqrt();d=abssq(delta).sqrt();aa=abssq(z[0]);bb=abssq(z[3]);ff=abssq(z[2])
  if c==0:return None,(aa<1 and bb<1),float(ff/((1-aa)*(1-bb))) if aa<1 and bb<1 else None
  k=(1-aa-bb+d*d)/(2*c);stable=k>1 and d<1
  mag=abssq(z[2]).sqrt()/abssq(z[1]).sqrt()*(k-(k*k-1).sqrt()) if stable else None
  kf=float(k);return kf if math.isfinite(kf) else None,stable,float(mag) if mag is not None else None
def fcmul(a,b):return a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]
def fcdiv(a,b):
 d=b[0]*b[0]+b[1]*b[1];return (a[0]*b[0]+a[1]*b[1])/d,(a[1]*b[0]-a[0]*b[1])/d
def fc(z):return F(z.real),F(z.imag)
def fcadd(a,b):return a[0]+b[0],a[1]+b[1]
def fcsub(a,b):return a[0]-b[0],a[1]-b[1]
def noise_matrix(values):return np.array([[complex(z['re'],z['im']) for z in row] for row in values]).reshape(-1,2,2)
failure=None
try:
 stability_inputs=[]
 for reflection in [0.,1.-2.**-20,1.-2.**-50]:
  for reverse in [1e-2,1e-100,1e-200,1e-300,5e-324,0.]:
   m=np.array([[reflection,reverse],[2.,reflection]],dtype=complex);stability_inputs.append(m)
 stability_inputs.append(np.array([[.2+.1j,.03-.02j],[1.4+.1j,.1-.1j]]))
 for m in stability_inputs:
  expected_k,stable,expected_mag=stability_oracle(m)
  point=ask(text(m[None]),'stability')['stability'][0]
  assert point['unconditionally_stable']==bool(stable),(m,point,stable)
  if expected_k is not None:close(point['k'],expected_k,'Decimal800 Rollett K',rtol=2e-10,atol=1e-12)
  else:assert point.get('k') is None
  if expected_mag is not None:close(point['mag'],expected_mag,'Decimal800 original MAG',rtol=2e-10,atol=0.)
  else:assert point.get('mag') is None
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');other=float(rf.Network(f=[1],s=m[None],z0=50).max_gain[0])
  if stable and (not math.isfinite(other) or not np.isclose(other,expected_mag,rtol=1e-7,atol=0)):
   disagreements.append(dict(oracle='scikit-rf2.1.0 max_gain',observed=repr(other),decimal800=expected_mag,input=m.real.tolist(),reason='binary64 K^2 or near-unit-margin cancellation; Decimal original expression is used for this limit'))
 # Load/reference shapes include true matched zero, complex load and active load.
 m=np.array([[.1,.2],[.5,.3]],dtype=complex)
 for reference in [5e-324,1e-310,50.,1e308]:
  load=complex(reference,0.)
  out=ask(text(m[None],(50.,reference)),'terminate',terminations=[[1,load.real,load.imag]],impedance=True)
  close(out['values'][0][0]['re'],.1,'matched finite load')
 for reference,load in [(1e308,complex(1e308,1e308)),(1e-310,complex(2e-310,1e-310)),(1e308,complex(-.5e308,0))]:
  r=F(reference);z=fc(load);gamma=fcdiv((z[0]-r,z[1]),(z[0]+r,z[1]))
  denominator=(1-F(.3)*gamma[0],-F(.3)*gamma[1]);fraction=fcdiv(fcmul(fc(complex(.2*.5,0)),gamma),denominator)
  wanted=complex(float(F(.1)+fraction[0]),float(fraction[1]))
  out=ask(text(m[None],(50.,reference)),'terminate',terminations=[[1,load.real,load.imag]],impedance=True)
  got=complex(out['values'][0][0]['re'],out['values'][0][0]['im']);close(got,wanted,'Fraction complex impedance feedback')
 out=ask(text(m[None],(50.,1e308)),'terminate',terminations=[[1,-1e308,0]],impedance=True)
 close(out['values'][0][0]['re'],float(F(.1)-F(.2)*F(.5)/F(.3)),'Fraction load Gamma pole with nonsingular full feedback')
 singular=m.copy();singular[1,1]=.5
 ask(text(singular[None]),'terminate',terminations=[[1,-150.,0]],impedance=True,reject=True)
 # Exact two-load adjugate solution, unsorted terminated ports and one Gamma
 # pole. This checks the general matrix orientation rather than only t=1.
 s4=np.array([[.1,.02,.03,.04],[.05,.3,.07,.08],[.09,.1,.2,.12],[.13,.14,.15,.4]],dtype=complex)
 ports=[3,1];loads=[complex(-110,0),complex(75,25)];refs=[50.,75.,90.,110.];keep=[0,2]
 ns=[fcsub(fc(z),(F(refs[t]),F(0))) for t,z in zip(ports,loads)]
 ds=[fcadd(fc(z),(F(refs[t]),F(0))) for t,z in zip(ports,loads)]
 A=[[fcsub(ds[i] if i==j else (F(0),F(0)),fcmul(ns[i],fc(s4[ports[i],ports[j]]))) for j in range(2)] for i in range(2)]
 det=fcsub(fcmul(A[0][0],A[1][1]),fcmul(A[0][1],A[1][0]));wanted=np.empty((2,2),complex)
 for column,pin in enumerate(keep):
  rhs=[fcmul(ns[i],fc(s4[ports[i],pin])) for i in range(2)]
  solved=[fcdiv(fcsub(fcmul(rhs[0],A[1][1]),fcmul(A[0][1],rhs[1])),det),
          fcdiv(fcsub(fcmul(A[0][0],rhs[1]),fcmul(rhs[0],A[1][0])),det)]
  for row,pout in enumerate(keep):
   value=fc(s4[pout,pin])
   for i in range(2):value=fcadd(value,fcmul(fc(s4[pout,ports[i]]),solved[i]))
   wanted[row,column]=complex(float(value[0]),float(value[1]))
 result=ask(text(s4[None],refs),'terminate',terminations=[[t,z.real,z.imag] for t,z in zip(ports,loads)],impedance=True)
 got=np.array([complex(z['re'],z['im']) for z in result['values'][0]]).reshape(2,2)
 close(got,wanted,'Fraction unsorted multiple loads including Gamma pole')
 assert result['reference_ohms']==[50.,90.]
 # Two-frequency covariance interpolation with real, tiny but nonzero Rn.
 s=np.tile(np.array([[0.,.5],[.5,0.]],dtype=complex),(2,1,1))
 for reference in [1.,50.,1e6]:
  for rn in [1e-200,1e-14,.1]:
   t=text(s,(reference,reference),[rn,3*rn]);nt=rf.Network(f=[1,2],s=s,z0=reference)
   nt.set_noise_a(noise_freq=nt.frequency,nfmin_db=np.array([0.,0.]),gamma_opt=np.array([0j,0j]),rn=np.array([rn,3*rn]))
   wanted=nt.interpolate([1.,1.5,2.])
   result=ask(t,'interpolate',frequency_hz=[1.,1.5,2.])
   points=ask(result['text'],'inspect')['noise']
   close(np.array([x['resistance_ohms'] for x in points])/rn,wanted.rn/rn,'independent small-Rn interpolation',rtol=2e-11,atol=0.)
   result=ask(result['text'],'noise',source=[.1,.1],figure_db=3.)
   close(noise_matrix(result['a'])/rn,wanted.noise/(4*K_BOLTZMANN*T0)/rn,'independent normalized chain covariance',rtol=2e-10,atol=1e-13)
 # A verified independent covariance at the intermediate stage prevents this
 # small-noise cascade/deembedding consumer from being only a self roundtrip.
 left=rf.Network(f=[1,2],s=s,z0=50)
 dut=rf.Network(f=[1,2],s=s,z0=50)
 dut.set_noise_a(noise_freq=dut.frequency,nfmin_db=np.array([0.,0.]),gamma_opt=np.array([0j,0j]),rn=np.array([1e-14,3e-14]))
 total=left**dut
 cascaded=ask(text(s,noise=[1e-14,3e-14]),'cascade',right=text(s))
 # Library cascade is DUT followed by the noiseless block, matching this oracle.
 total=dut**left
 cov=ask(cascaded['text'],'noise',source=[.1,.1],figure_db=3.)
 close(noise_matrix(cov['a'])/1e-14,total.noise/(4*K_BOLTZMANN*T0)/1e-14,'independent tiny-noise cascade covariance',rtol=2e-10,atol=1e-13)
 thru=np.tile(np.array([[0.,1.],[1.,0.]],dtype=complex),(2,1,1))
 recovered=ask(cascaded['text'],'deembed',left=text(thru),right=text(s))
 cov=ask(recovered['text'],'noise',source=[.1,.1],figure_db=3.)
 close(noise_matrix(cov['a'])/1e-14,dut.noise/(4*K_BOLTZMANN*T0)/1e-14,'independent tiny-noise recovered DUT covariance',rtol=2e-10,atol=1e-13)
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 out=dict(complete=failure is None,failure=repr(failure) if failure else None,requests=len(raw),checks=checks,raw=raw,
 primaryReference=dict(scikit_rf=rf.__version__,numpy=np.__version__,maxGainSource=inspect.getsource(rf.Network.max_gain.fget),
 url='https://raw.githubusercontent.com/scikit-rf/scikit-rf/v2.1.0/skrf/network.py'),oracleDisagreements=disagreements,
 sourceSHA256={k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['amplifier.mbt','noise.mbt','tools/verify-rf-extreme.py']})
 args.evidence.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:out[k] for k in ['complete','failure','requests','oracleDisagreements']},indent=2))
if failure:raise failure
