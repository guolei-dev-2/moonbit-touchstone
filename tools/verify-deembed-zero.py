"""Known-fixture zero-forward recovery: independent Fraction wave connections."""
import argparse,hashlib,json,math,os,subprocess
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def connect(a,b):
    # Solve the two connected boundary-wave equations, without T/ABCD or S21 division.
    denominator=1-a[3]*b[0]
    return [a[0]+a[1]*b[0]*a[2]/denominator,a[1]*b[1]/denominator,b[2]*a[2]/denominator,b[3]+b[2]*a[3]*b[1]/denominator]

def text(matrices,refs,frequencies,information=()):
    result='[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] '+str(len(matrices))+'\n[Reference] '+' '.join(map(str,refs))+'\n'
    if information:result+='[Begin Information]\n'+'\n'.join(information)+'\n[End Information]\n'
    result+='[Network Data]\n'
    for frequency,matrix in zip(frequencies,matrices):result+=str(frequency)+' '+' '.join(str(float(v))+' 0' for v in matrix)+'\n'
    return result+'[End]\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--before',type=Path)
    args=parser.parse_args()
    assert not args.evidence.exists(),'choose a new evidence path'
    work=args.evidence.with_suffix('.cases');work.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,NODE_DISABLE_COMPILE_CACHE='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(work),TMP=str(work),TMPDIR=str(work))
    sources=['cascade.mbt','noise.mbt','mixed_mode.mbt','deembed_zero_test.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','tools/verify-deembed-zero.py','examples/deembed-opaque.s2p','examples/deembed-thru.s2p','examples/deembed-zero-options.json']
    bridge=ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
    report={'complete':False,'failure':None,'sourceSHA256':{p:sha(ROOT/p) for p in sources},'bridgeSHA256':sha(bridge),'oracle':'Exact Fraction independent connected boundary waves generating measured data from known original DUTs; recovered S compared to originals, then actual file metrics checked','absoluteMatrixTolerance':2e-12,'commands':[],'checks':[],'recoveredSamples':3,'oldCollectionsRerun':False,'newManufacturerInputs':0,'nodeCompileCacheDisabled':True}
    def write(name,content):
        path=work/name;path.write_text(content,encoding='ascii');return path
    def run(name,command,input_path,options,output=None,expected_exit=0):
        option=write(name+'.options.json',json.dumps(options)+'\n')
        argv=['node',str(ROOT/'tools/touchstone.mjs'),command,str(input_path),'@'+str(option)]
        if output is not None:argv.append(str(output))
        result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        for stream in ['stdout','stderr']:(work/(name+'.'+stream+'.log')).write_text(getattr(result,stream),encoding='utf-8')
        report['commands'].append({'name':name,'command':argv,'exitCode':result.returncode,'expectedExitCode':expected_exit,'stdout':str(work/(name+'.stdout.log')),'stderr':str(work/(name+'.stderr.log'))})
        assert result.returncode==expected_exit,(name,result.stdout,result.stderr)
        if expected_exit:assert not result.stdout and result.stderr.startswith('touchstone:')
        return result.stdout
    def near(a,b,tolerance=2e-12):
        assert isinstance(a,(int,float)) and not isinstance(a,bool) and math.isfinite(a)
        assert abs(a-float(b))<=tolerance,(a,b)
    try:
        left=[F(1,10),F(1,2),F(2,5),F(1,5)]
        right=[-F(1,10),F(3,5),F(7,10),F(1,6)]
        dut=[[F(0)]*4,[F(1,4),F(3,10),F(0),-F(1,5)],[F(1,4),F(3,10),F(2,5),-F(1,5)]]
        measured=[connect(connect(left,d),right) for d in dut]
        frequencies=[1e9,2e9,3e9];information=['Zero forward DUT sweep','Known independent fixture wave model']
        lp=write('left.s2p',text([left]*3,[50,75],frequencies))
        rp=write('right.s2p',text([right]*3,[60,100],frequencies))
        mp=write('measured.s2p',text(measured,[50,100],frequencies,information))
        recovered=work/'recovered.s2p'
        run('deembed-write','deembed',mp,{'left_file':str(lp),'right_file':str(rp)},recovered)
        assert recovered.is_file()
        report['checks'].append('A real three-point recovered Touchstone file is created by the existing deembed command')
        dump=json.loads(run('dump-recovered','dump',recovered,{}))
        assert dump['frequency_hz']==frequencies and len(dump['values'])==3
        for actual,original in zip(dump['values'],dut):
            for value,expected in zip(actual,original):near(value['re'],expected);near(value['im'],0)
        report['checks'].append('Opaque, reverse-only and ordinary recovered S match independent original DUT matrices')
        metadata=json.loads(run('inspect-recovered','inspect',recovered,{}))
        assert metadata['reference_ohms']==[75,60] and dump['reference_ohms']==[75,60]
        assert metadata['information']==information and metadata['noise']==[] and metadata['mixed_mode_order']==[]
        report['checks'].append('Output uses fixture inner references and preserves measurement information without invented noise')
        metrics=json.loads(run('metrics-recovered','metrics',recovered,{'input':0,'output':1}))
        assert len(metrics)==3
        for i,row in enumerate(metrics):
            assert row['frequency_hz']==frequencies[i]
            near(row['transmission_magnitude'],dut[i][2])
            if i<2:assert row['insertion_loss_infinite'] is True and 'insertion_loss_db' not in row
            else:assert row['insertion_loss_infinite'] is False;near(row['insertion_loss_db'],-20*math.log10(.4),2e-10)
            near(row['vswr'],1 if i==0 else 5/3)
        report['checks'].append('The actual recovered file feeds metrics with exact zero-transmission loss flags and a finite ordinary sample')
        ordinary=write('ordinary.s2p',text([[F(1,10),F(1,5),F(3,10),F(1,10)]],[50,50],[1e9],['Known fixture identity control']))
        through=ROOT/'examples/deembed-thru.s2p'
        ordinary_output=run('ordinary-compatible','deembed',ordinary,{'left_file':str(through),'right_file':str(through)})
        if args.before:
            baseline=json.loads(args.before.read_text(encoding='utf-8'))
            assert ordinary_output==baseline['initialControls']['ordinaryStdout']
        report['checks'].append('Ordinary nonzero-forward control completes, with exact pre-repair text comparison when baseline supplied')
        singular=write('singular-left.s2p',text([[F(0),F(0),F(1,2),F(0)]]*3,[50,75],frequencies))
        run('singular-fixture','deembed',mp,{'left_file':str(singular),'right_file':str(rp)},expected_exit=2)
        report['checks'].append('A noninvertible fixture remains an error before the zero-forward fallback')
        pole_left=write('pole-left.s2p',text([[F(0),F(1,2),F(1,2),F(1,2)]],[50,50],[1e9]))
        pole=write('pole-measured.s2p',text([[-F(1,2),F(0),F(0),F(0)]],[50,50],[1e9]))
        run('true-recovery-pole','deembed',pole,{'left_file':str(pole_left),'right_file':str(through)},expected_exit=2)
        report['checks'].append('A genuine nonrepresentable recovery denominator remains an error')
        opaque=ROOT/'examples/deembed-opaque.s2p'
        opaque_output=run('original-opaque','deembed',opaque,{'left_file':str(through),'right_file':str(through)})
        tokens=opaque_output.split('[Network Data]\n',1)[1].split('[End]',1)[0].split()
        assert len(tokens)==9 and float(tokens[0])==1e9 and all(float(v)==0 for v in tokens[1:])
        report['checks'].append('The original ideal-through opaque counterexample now recovers finite all-zero S')
        if args.before:assert sha(opaque)==baseline['inputSHA256']['opaque.s2p']
        report['checks'].append('The opaque input bytes remain identical to the original baseline when supplied')
        report['baselineCompared']=args.before is not None
        report['expectedDUT']=[[[float(v),0.0] for v in d] for d in dut]
        report['measuredFractions']=[[str(v) for v in m] for m in measured]
        report['recoveredSHA256']=sha(recovered)
        report['complete']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:
        report['actualFileCLINodeProcesses']=len(report['commands']);report['consumerChecks']=len(report['checks'])
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'complete':True,'actualFileCLINodeProcesses':report['actualFileCLINodeProcesses'],'consumerChecks':report['consumerChecks'],'recoveredSamples':3}))
if __name__=='__main__':main()
