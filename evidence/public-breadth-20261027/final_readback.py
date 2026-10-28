"""Final static source/receipt/private-data readback, no target execution."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

E=Path(__file__).resolve().parent
ROOT=E.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text('utf-8'))
source=load(E/'SOURCE.json');result=load(E/'RESULT.json');build=load(E/'BUILD.json')
private=Path(source['privateExcludedDirectory'])
assert private.resolve()!=ROOT.resolve() and ROOT.resolve() not in private.resolve().parents
assert source['manufacturer']=='NXP Semiconductors' and source['priorManufacturer'].startswith('Johanson')
assert source['redistributionPermissionConfirmed'] is False
assert sha((private/'BFU530W_Spar.zip').read_bytes())==source['archiveSHA256']
with zipfile.ZipFile(private/'BFU530W_Spar.zip') as z:
    assert z.read(source['selectedMember'])==(private/source['selectedMember']).read_bytes()
assert sha((private/source['selectedMember']).read_bytes())==source['selectedSHA256']==result['inputSHA256']
assert result['frequencyPoints']==98 and result['ports']==2
assert all(c['complexValuesCompared']==392 and c['frequencyAndReferenceExactlyEqual'] for c in result['checks'])
assert len(result['actualCommands'])==3 and all(c['exitCode']==0 for c in result['actualCommands'])
for command in result['actualCommands']:
    for stream in ['stdout','stderr']:
        f=Path(command[stream+'PrivatePath'])
        assert private.resolve() in f.resolve().parents
        assert sha(f.read_bytes())==command[stream+'SHA256']
before=load(E/'INPUTS-BEFORE.json')['files']
assert len(before)==46 and all(sha((ROOT/n).read_bytes())==v for n,v in before.items())
assert sha(Path(build['enginePath']).read_bytes())==build['engineSHA256']==result['currentEngineSHA256']
terminal=load(E/'build.terminal.json')
assert terminal['exitCode']==0
assert sha((E/'build.stdout.raw').read_bytes())==terminal['stdoutSHA256']
assert sha((E/'build.stderr.raw').read_bytes())==terminal['stderrSHA256']
for md in [ROOT/'README.md',E/'README.md']:
    for target in re.findall(r'\]\(([^)]+)\)',md.read_text('utf-8')):
        if target.startswith(('http://','https://','#')):continue
        assert (md.parent/target.split('#')[0]).exists(),(md,target)
assert not list(E.rglob('*.s2p')) and not list(E.rglob('*.zip'))
excluded=load(E/'PACKAGE-EXCLUSIONS.json')
assert Path(excluded['excludeAbsoluteDirectory']).resolve()==private.resolve() and excluded['recursive']
private_inventory=[dict(path=f.relative_to(private).as_posix(),bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
                   for f in sorted(private.rglob('*')) if f.is_file()]
with (E/'PRIVATE-FILE-HASHES.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(dict(excludeEntireDirectory=str(private),redistributionPermissionConfirmed=False,
                   containsNoVendorValues=True,files=private_inventory),f,ensure_ascii=False,indent=2);f.write('\n')
inventory=[dict(path=f.relative_to(E).as_posix(),bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
           for f in sorted(E.rglob('*')) if f.is_file()]
receipt=dict(schema=1,status='original-vendor-breadth-feedback-locally-remedied',
             priorManufacturer='Johanson Technology',newManufacturer='NXP Semiconductors',combinedEvidenceVendors=2,
             newDevice='BFU530W',selectedMember=source['selectedMember'],inputSHA256=source['selectedSHA256'],
             newFrequencyPoints=98,newComplexValuesPerCheck=392,independentChecks=3,
             currentModule='guolei-dev/touchstone@0.3.0',engineSHA256=build['engineSHA256'],
             sourceInputCount=46,allSourceInputsUnchanged=True,newAlgorithmChanges=0,
             currentCLIStrictJSBuildExitCode=0,newCLICommandExitCodes=[0,0,0],
             referenceRuntime=result['referenceRuntime'],prior30or1103SuiteRerun=False,oldPublicSampleRerun=False,
             realExecutionToolObservations=[dict(chunk='d89485',exitCode=0,scope='one current strict JS build controller'),
                                            dict(chunk='6abefd',exitCode=0,scope='new-input-only scikit-rf/NumPy verifier; raw CLI data preserved privately')],
             producerFailuresPreserved=['FETCH-01-FAILURE.json','SOURCE.json: earlierAttempts'],
             modifiedExistingFiles=['README.md'],newEvidenceDirectory=str(E),publicFiles=inventory,
             mainReadmeSHA256=sha((ROOT/'README.md').read_bytes()),
             originalDataExcludedDirectory=str(private),privateHashManifest='PRIVATE-FILE-HASHES.json',
             publicDirectoryHasNoOriginalArchiveOrS2P=True,allCurrentLinksExist=True,allReadbacksPassed=True,
             formalContestAcceptanceClaim=False,manufacturerEndorsementClaim=False,externalAdoptionClaim=False,
             allManufacturersOrBiasesClaim=False,newPhysicalMeasurementClaim=False,fullProjectComplete=False,
             conclusion='Adds one genuine first-party NXP bias file and independent current-CLI numerical/read-write evidence; does not rerun or redate Johanson history or certify all manufacturer data.')
with (E/'CLOSURE.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
assert load(E/'CLOSURE.json')==receipt
print(json.dumps(dict(receipt=str(E/'CLOSURE.json'),sha256=sha((E/'CLOSURE.json').read_bytes()),
                     resultSHA256=sha((E/'RESULT.json').read_bytes()),sourceSHA256=sha((E/'SOURCE.json').read_bytes()),
                     packageExclusionsSHA256=sha((E/'PACKAGE-EXCLUSIONS.json').read_bytes()),
                     mainREADMEsha256=sha((ROOT/'README.md').read_bytes()),readbacksPassed=True,
                     privateExcluded=str(private),newTargetRunsAfterPassingVerification=0),ensure_ascii=False))
