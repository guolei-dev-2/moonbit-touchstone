"""Validate only the one new NXP input with current CLI + scikit-rf/NumPy.

All original or fully materialized manufacturer data stay in the private
directory. The distributable report contains identity, counts and errors.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import numpy as np
import skrf as rf

E = Path(__file__).resolve().parent
ROOT = E.parents[1]
DEFAULT_PRIVATE = Path('D:/CodexLocal/ban/work/portfolio-progress-20261027/private-reference-inputs/touchstone-breadth-20261027')
DEFAULT_NODE = Path('C:/Program Files/nodejs/node.exe')
MEMBER = 'BFU530W_03V3_001mA_SP.s2p'
EXPECTED = 'd4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95'
sha = lambda b: hashlib.sha256(b).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--private-directory',type=Path,default=DEFAULT_PRIVATE)
parser.add_argument('--node',type=Path,default=DEFAULT_NODE)
args = parser.parse_args()
private = args.private_directory.resolve()
sample = private/MEMBER
assert sha(sample.read_bytes()) == EXPECTED
build = json.loads((E/'BUILD.json').read_text('utf-8'))
assert sha(Path(build['enginePath']).read_bytes()) == build['engineSHA256']
output = private/'new-input-validation'
output.mkdir(exist_ok=False)
commands=[]


def cli(command, options, target):
    argv = [str(args.node),str(ROOT/'tools/touchstone.mjs'),command,str(sample),json.dumps(options,separators=(',',':'))]
    stdout=output/target; stderr=output/(target+'.stderr')
    start=time.perf_counter_ns()
    with stdout.open('xb') as out, stderr.open('xb') as err:
        process=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        code=process.wait(timeout=30)
    terminal=dict(command=argv,cwd=str(ROOT),pid=process.pid,exitCode=code,
                  elapsedNs=time.perf_counter_ns()-start,stdoutPrivatePath=str(stdout),stderrPrivatePath=str(stderr),
                  stdoutSHA256=sha(stdout.read_bytes()),stderrSHA256=sha(stderr.read_bytes()))
    commands.append(terminal)
    with (E/(command+'.terminal.json')).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(terminal,f,indent=2);f.write('\n')
    assert code==0,terminal
    return stdout


reference=rf.Network(str(sample))
assert reference.nports==2 and np.isfinite(reference.s).all()
dump=json.loads(cli('dump',{},'dump.json').read_text('utf-8'))
actual=np.array([[z['re']+1j*z['im'] for z in row] for row in dump['values']]).reshape(-1,2,2)
np.testing.assert_array_equal(dump['frequency_hz'],reference.f)
np.testing.assert_array_equal(dump['reference_ohms'],reference.z0[0].real)
assert np.all(reference.z0 == 50)
np.testing.assert_allclose(actual,reference.s,rtol=3e-10,atol=3e-12)
converted=json.loads(cli('rf-convert',{'parameter':'Y'},'y.json').read_text('utf-8'))
actual_y=np.array([[z['re']+1j*z['im'] for z in row] for row in converted['values']]).reshape(-1,2,2)
np.testing.assert_array_equal(converted['frequency_hz'],reference.f)
np.testing.assert_array_equal(converted['reference_ohms'],reference.z0[0].real)
np.testing.assert_allclose(actual_y,reference.y,rtol=3e-10,atol=3e-12)
normalized=cli('normalize',{},'normalized.s2p')
written=rf.Network(str(normalized))
np.testing.assert_array_equal(written.f,reference.f)
np.testing.assert_array_equal(written.z0,reference.z0)
np.testing.assert_allclose(written.s,reference.s,rtol=3e-10,atol=3e-12)
assert len(reference.f)>1 and reference.f[0]==40e6 and reference.f[-1]==6e9
inputs=json.loads((E/'INPUTS-BEFORE.json').read_text('utf-8'))['files']
assert all(sha((ROOT/n).read_bytes())==expected for n,expected in inputs.items())
report=dict(status='passed-new-first-party-manufacturer-input',manufacturer='NXP Semiconductors',device='BFU530W',
            selectedMember=MEMBER,inputBytes=sample.stat().st_size,inputSHA256=EXPECTED,
            manufacturerSource='https://www.nxp.com/downloads/en/s-parameters/BFU530W_Spar.zip',
            ports=reference.nports,frequencyPoints=len(reference.f),frequencyRangeHz=[float(reference.f[0]),float(reference.f[-1])],
            format='MHz S MA R50',referenceOhms=[50,50],
            checks=[dict(name='current CLI dump vs scikit-rf S',complexValuesCompared=int(reference.s.size),
                         frequencyAndReferenceExactlyEqual=True,maxComplexAbsoluteError=float(np.max(np.abs(actual-reference.s))),rtol=3e-10,atol=3e-12),
                    dict(name='current CLI S-to-Y vs scikit-rf Y',complexValuesCompared=int(reference.y.size),
                         frequencyAndReferenceExactlyEqual=True,maxComplexAbsoluteError=float(np.max(np.abs(actual_y-reference.y))),rtol=3e-10,atol=3e-12,units='siemens'),
                    dict(name='current CLI normalize output independently reread by scikit-rf',complexValuesCompared=int(reference.s.size),
                         frequencyAndReferenceExactlyEqual=True,maxComplexAbsoluteError=float(np.max(np.abs(written.s-reference.s))),rtol=3e-10,atol=3e-12)],
            actualCommands=commands,allExitCodesZero=True,
            referenceRuntime=dict(python=sys.version,executable=sys.executable,scikitRF=rf.__version__,numpy=np.__version__,
                                  skrfSourcePath=rf.__file__,skrfSourceSHA256=sha(Path(rf.__file__).read_bytes()),
                                  numpySourcePath=np.__file__,numpySourceSHA256=sha(Path(np.__file__).read_bytes())),
            nodePath=str(args.node),nodeSHA256=sha(args.node.read_bytes()),
            currentEnginePath=build['enginePath'],currentEngineSHA256=build['engineSHA256'],sourceInputsUnchanged=True,
            newManufacturers=1,historicalManufacturer='Johanson Technology',vendorCountInCombinedEvidence=2,
            priorReferenceTestsRerun=0,oldPublicSamplesRerun=0,algorithmFilesChanged=0,
            privateFullDataDirectory=str(private),redistributionPermissionConfirmed=False,
            limits=['One selected manufacturer bias file, not all 36 archive files or all vendors.',
                    'Official manufacturer model data are real first-party data; not a newly performed VNA measurement.',
                    'Independent software numerical/format comparison, not device qualification or external adoption.',
                    'Original archive, S2P and full-value/rewritten outputs are private and excluded from distributed packages.'])
with (E/'RESULT.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({key:report[key] for key in ['status','frequencyPoints','ports','checks','allExitCodesZero','sourceInputsUnchanged']},ensure_ascii=False))
