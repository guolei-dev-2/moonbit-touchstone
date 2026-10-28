"""Independent exact normalization/degree-period fixtures and metadata consumer.

Reference resistances are powers of two with EVEN exponents; their square roots
and all normalization factors are exact rational numbers. Fraction expectations
do not use the library's binary scaling algorithm or a self roundtrip. Degree
remainders use exact rationals of the parsed binary64 value before small-angle
trigonometry. No downloaded input or historical suite is used.
"""
import argparse,hashlib,json,math,subprocess
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
if args.evidence.exists():p.error('use fresh receipt path')
host=subprocess.Popen(['node','tools/oracle-host.mjs'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,encoding='utf-8')
raw=[];checks=[]
def ask(text,command='dump',ports=None,reject=False,**opts):
 if ports is not None:opts['ports']=ports
 q=dict(text=text,options=dict(command=command,**opts));host.stdin.write(json.dumps(q)+'\n');host.stdin.flush()
 line=host.stdout.readline();assert line,'bridge stopped';r=json.loads(line);raw.append(dict(query=q,response=r));assert r['ok']!=reject,r
 return r.get('result')
def coeff(kind,row,col,e):
 if kind=='S':return F(1)
 sr=1 if kind=='Z' or kind=='H' and row==0 or kind=='G' and row==1 else -1
 sc=1 if kind=='Z' or kind=='H' and col==0 or kind=='G' and col==1 else -1
 power=(sr*e[row]+sc*e[col])//2
 return F(2)**power
def file(kind,m,refs,legacy):
 n=len(refs);lines=[]
 if not legacy:lines.append('[Version] 2.1')
 lines.append(f'# Hz {kind} RI R '+' '.join(format(v,'.17g') for v in (refs if legacy else refs[:1])))
 if not legacy:
  lines += [f'[Number of Ports] {n}','[Number of Frequencies] 1','[Reference] '+' '.join(format(v,'.17g') for v in refs)]
  if n==2:lines.append('[Two-Port Data Order] 12_21')
  lines.append('[Network Data]')
 order=[0,2,1,3] if n==2 and legacy else list(range(n*n))
 lines.append('1 '+' '.join(format(v,'.17g') for k in order for v in [m[k].real,m[k].imag]))
 if not legacy:lines.append('[End]')
 return '\n'.join(lines)+'\n'
def close(actual,expected,label,rtol=3e-14,atol=2e-323):
 for a,b in zip(actual,expected):
  assert abs(a-b) <= max(atol,abs(b)*rtol),(label,a,b)
 checks.append(dict(label=label,values=len(expected)))
def flattened(result):return [v for z in result['values'][0] for v in [z['re'],z['im']]]
failure=None
try:
 for e in [(-1074,1022),(1000,-1000),(2,4)]:
  refs=[math.ldexp(1.,k) for k in e]
  for kind in ['S','Y','Z','H','G']:
   factors=[coeff(kind,k//2,k%2,e) for k in range(4)]
   values=[];expected=[]
   for k,factor in enumerate(factors):
    # Chosen finite binary64 inputs counterbalance out-of-range intermediate
    # factors. No failing input is discarded after seeing the implementation.
    exponent=factor.numerator.bit_length()-factor.denominator.bit_length()
    power=max(-1074,min(1000,-exponent))
    z=complex(math.ldexp(.75,power),math.ldexp(-.25,power));values.append(z)
    expected.extend([float(F(z.real)*factor),float(F(z.imag)*factor)])
   actual=ask(file(kind,values,refs,True),ports=2)
   close(flattened(actual),expected,'Fraction legacy '+kind+' input '+str(e))
   physical=[complex(expected[2*k],expected[2*k+1]) for k in range(4)]
   emitted=ask(file(kind,physical,refs,False),'legacy',format='RI')['text']
   # Read numeric output layout without applying any RF normalization.
   tokens=[float(x) for line in emitted.splitlines() if not line.startswith('#') for x in line.split()]
   order=[0,2,1,3];got=[0.]*8
   for j,k in enumerate(order):got[2*k:2*k+2]=tokens[1+2*j:3+2*j]
   wanted=[float(F(v)/factors[k]) for k,z in enumerate(physical) for v in [z.real,z.imag]]
   close(got,wanted,'Fraction independent legacy '+kind+' output '+str(e))
 # Genuine unrepresentable final values still fail rather than emitting Inf/NaN.
 ask('# Hz Z RI R 1e308\n1 1e308 0\n',ports=1,reject=True)
 ask('[Version] 2.1\n# Hz Y RI R 1e308\n[Number of Ports] 1\n[Number of Frequencies] 1\n[Network Data]\n1 1e308 0\n[End]\n','legacy',reject=True)
 for degrees in [3.6e21,-3.6e21,2.**80,1e308,-1e308,720.25,-720.25,45.]:
  remainder=float(F(degrees)%360)
  if remainder>180:remainder-=360
  for fmt,amplitude,magnitude in [('MA',.75,.75),('DB',0.,1.)]:
   expected=[magnitude*math.cos(math.radians(remainder)),magnitude*math.sin(math.radians(remainder))]
   for version in [1,2]:
    options=f'# Hz S {fmt} R 50\n';body=f'1 {amplitude:.17g} {degrees:.17g}\n'
    t=options+body if version==1 else '[Version] 2.1\n'+options+'[Number of Ports] 1\n[Number of Frequencies] 1\n[Network Data]\n'+body+'[End]\n'
    close(flattened(ask(t,ports=1)),expected,'exact degree period '+fmt+' v'+str(version),rtol=2e-13,atol=2e-14)
 # Noise Gamma uses the same degree rule, while its option-line reference and
 # information lines must survive canonical writing independently of [Reference].
 t='[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 1\n[Two-Port Data Order] 12_21\n[Reference] 75 75\n[Number of Noise Frequencies] 1\n[Begin Information]\nfixture ! retained\n[End Information]\n[Network Data]\n10 0 0 .5 0 .5 0 0 0\n[Noise Data]\n1 0 .5 3.6e21 1\n[End]\n'
 for source in [t,ask(t,'normalize')['text']]:
  d=ask(source,'inspect');assert d['information']==['fixture ! retained']
  assert d['noise_reference_ohms']==50 and d['reference_ohms']==[75,75]
  close([d['noise'][0]['gamma_opt']['re'],d['noise'][0]['gamma_opt']['im']],[.5,0.],'noise Gamma degrees and metadata')
 # Analytic secants of phase [0,-pi/2,-pi] on an uneven frequency grid.
 for scale in [1.,1e-200]:
  t='# Hz S RI R 50\n0 1 0\n'+f'{scale:.17g} 0 -1\n{3*scale:.17g} -1 0\n'
  close(ask(t,'delay',ports=1,input=0,output=0),[.25/scale,(1/6)/scale,.125/scale],'nonuniform group-delay secants',rtol=2e-14,atol=0.)
 # Primary standard says these are invalid, unlike the finite counterexamples.
 ask(t.replace('0 1 0','0 0 0'),'delay',ports=1,input=0,output=0,reject=True)
except Exception as e:failure=e
finally:
 host.stdin.close();host.wait(timeout=10)
 result=dict(complete=failure is None,failure=repr(failure) if failure else None,requests=len(raw),checks=checks,raw=raw,
 primarySpecification={'url':'https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf','version':'2.1,2024-01-26',
 'sections':['p4 angles in degrees','p8 legacy voltage/current normalization','p10 noise count greater than zero','p28 information placement']},
 sourceSHA256={k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in ['text.mbt','legacy.mbt','versioned.mbt','document.mbt','analysis.mbt','tools/verify-format-extreme.py']})
 args.evidence.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['complete','failure','requests']},indent=2))
if failure:raise failure
