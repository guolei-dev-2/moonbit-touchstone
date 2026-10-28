"""Independent Decimal norm-ratio and actual modal file consumer regression."""
import argparse
import hashlib
import json
import math
import os
import subprocess
from decimal import Decimal, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ZERO=(0.0,0.0)
LARGE=(1.5e308,1.5e308)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def fixture(values):
    dd,dc,cd,cc,reflection=values
    matrix=[ZERO]*16
    for index,value in [(0,reflection),(4,dd),(6,dc),(12,cd),(14,cc)]:matrix[index]=value
    rows=[' '.join(str(v) for z in matrix[row*4:(row+1)*4] for v in z) for row in range(4)]
    return '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 4\n[Number of Frequencies] 1\n[Mixed-Mode Order] D1,2 D3,4 C1,2 C3,4\n[Network Data]\n1000000000 '+rows[0]+'\n'+'\n'.join(rows[1:])+'\n[End]\n'

def squared_norm(value):
    x,y=map(Decimal.from_float,value)
    return x*x+y*y

def expected(values,definition):
    dd,dc,cd,cc,reflection=values
    with localcontext() as ctx:
        ctx.prec=100
        losses={}
        for key,value in [('differential_insertion_loss_db',dd),('differential_return_loss_db',reflection),('dc_conversion_loss_db',dc),('cd_conversion_loss_db',cd)]:
            norm=squared_norm(value)
            losses[key]=str(-10*norm.log10()) if norm else None
        a=squared_norm(dd)
        b=squared_norm({'balanced':cc,'input':dc,'output':cd}[definition])
        state='undefined' if not a and not b else 'positive_infinity' if not b else 'negative_infinity' if not a else 'finite'
        cmrr=str(10*(a/b).log10()) if a and b else None
        return {'losses':losses,'cmrr_state':state,'cmrr_db':cmrr}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--before',type=Path,help='Optional immutable round24 BASELINE.json')
    args=parser.parse_args()
    assert not args.evidence.exists(),'choose a new evidence path'
    work=args.evidence.with_suffix('.cases')
    work.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,NODE_DISABLE_COMPILE_CACHE='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(work),TMP=str(work))
    sources=['mixed_mode.mbt','modal_scale_test.mbt','gain.mbt','noise.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-modal-scale.py','examples/modal-scale.s4p','examples/modal-scale-options.json']
    bridge=ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
    report={'complete':False,'failure':None,'sourceSHA256':{p:sha(ROOT/p) for p in sources},'bridgeSHA256':sha(bridge),'oracle':'Decimal100 direct squared norms: loss=-10log10(re^2+im^2), CMRR=10log10(norm_desired/norm_denominator); exact zeros classify separately','absoluteToleranceDb':2e-10,'commands':[],'checks':[],'oldCollectionsRerun':False,'newManufacturerInputs':0,'nodeCompileCacheDisabled':True,'tempDirectory':str(work)}
    cases=[('large',(LARGE,ZERO,ZERO,LARGE,ZERO),'balanced'),('ordinary',((.5,.5),ZERO,ZERO,(.5,.5),ZERO),'balanced')]
    cases.extend(('all-large-'+definition,(LARGE,LARGE,LARGE,LARGE,LARGE),definition) for definition in ['balanced','input','output'])
    cases.extend((state,((a,0.0),(b,0.0),(b,0.0),(b,0.0),ZERO),'balanced') for state,a,b in [('undefined',0.0,0.0),('positive_infinity',.5,0.0),('negative_infinity',0.0,.25),('finite',.5,.25)])
    ordinary_stdout=None
    try:
        for name,values,definition in cases:
            input_path=work/(name+'.s4p')
            if name=='large':input_path.write_bytes((ROOT/'examples/modal-scale.s4p').read_bytes())
            else:input_path.write_text(fixture(values),encoding='ascii')
            options=work/(name+'.options.json')
            options.write_text(json.dumps({'output_pair':1,'input_pair':0,'cmrr':definition})+'\n',encoding='ascii')
            command=['node',str(ROOT/'tools/touchstone.mjs'),'modal-metrics',str(input_path),'@'+str(options)]
            run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
            for stream in ['stdout','stderr']:(work/(name+'.'+stream+'.log')).write_text(getattr(run,stream),encoding='utf-8')
            reference=expected(values,definition)
            report['commands'].append({'name':name,'command':command,'exitCode':run.returncode,'inputSHA256':sha(input_path),'expected':reference,'stdout':str(work/(name+'.stdout.log')),'stderr':str(work/(name+'.stderr.log'))})
            assert run.returncode==0,(name,run.stderr)
            rows=json.loads(run.stdout)
            assert len(rows)==1
            row=rows[0]
            assert row['frequency_hz']==1e9 and row['cmrr_definition']==definition
            for key,value in zip(['sdd','sdc','scd','scc'],values[:4]):
                assert row[key]=={'re':value[0],'im':value[1]},(name,key,row[key],value)
            assert row['cmrr_state']==reference['cmrr_state']
            for key,value in {**reference['losses'],'cmrr_db':reference['cmrr_db']}.items():
                if value is None:assert key not in row,(name,key,row)
                else:
                    actual=row[key]
                    assert isinstance(actual,(int,float)) and not isinstance(actual,bool) and math.isfinite(actual),(name,key,actual)
                    assert abs(Decimal.from_float(actual)-Decimal(value))<Decimal('2e-10'),(name,key,actual,value)
            if name=='ordinary':ordinary_stdout=run.stdout
        report['checks'].extend(['Nine actual file requests succeed','Modal complex elements, selected definition and frequency retain the input semantics','All four loss fields match Decimal squared-norm expectations or omit exact zero','CMRR values are finite numeric values matching direct Decimal norm ratios','All four exact zero/nonzero CMRR states and omitted fields remain distinct'])
        report['baselineCompared']=args.before is not None
        if args.before:
            before=json.loads(args.before.read_text(encoding='utf-8'))
            assert sha(ROOT/'examples/modal-scale.s4p')==before['inputSHA256']['large.s4p']
            report['checks'].append('The large input bytes are identical to the successfully parsed pre-repair counterexample')
            ordinary=next(row for row in before['records'] if row['name']=='ordinary-metrics')
            assert ordinary_stdout==ordinary['stdout']
            report['checks'].append('Complete ordinary finite file output remains byte-identical to before repair')
        report['complete']=True
    except Exception as error:
        report['failure']=repr(error)
        raise
    finally:
        report['actualFileCLINodeProcesses']=len(report['commands'])
        report['consumerChecks']=len(report['checks'])
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'complete':True,'actualFileCLINodeProcesses':report['actualFileCLINodeProcesses'],'consumerChecks':report['consumerChecks']}))

if __name__=='__main__':main()
