"""Bind the real first-party input and build the unchanged current CLI once."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import time
import zipfile

E = Path(__file__).resolve().parent
ROOT = E.parents[1]
PRIVATE = Path('D:/CodexLocal/ban/work/portfolio-progress-20261027/private-reference-inputs/touchstone-breadth-20261027')
MOON = Path('D:/CodexLocal/ban/work/acceptance-20260928/moon/bin/moon.exe')
MEMBER = 'BFU530W_03V3_001mA_SP.s2p'
EXPECTED_ZIP = '981d4f80f7ee35d273ce7917708c9f8ffded52372e71dff0ec57f99e41f78928'
sha = lambda b: hashlib.sha256(b).hexdigest()


def json_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


def product_inputs():
    return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(ROOT.rglob('*'))
            if p.is_file() and not set(p.relative_to(ROOT).parts)&{'evidence','_build','.git','.mooncakes'}
            and (p.suffix in {'.mbt','.mbti','.mjs','.py'} or p.name in {'moon.mod','moon.pkg','.moonbit-version'})}


raw = (PRIVATE/'BFU530W_Spar.zip').read_bytes()
assert sha(raw) == EXPECTED_ZIP
with zipfile.ZipFile(PRIVATE/'BFU530W_Spar.zip') as z:
    entries = [dict(path=i.filename, bytes=i.file_size, sha256=sha(z.read(i))) for i in z.infolist() if not i.is_dir()]
    assert len(entries) == 36 and all(i['path'].lower().endswith('.s2p') for i in entries)
    selected = z.read(MEMBER)
with (PRIVATE/MEMBER).open('xb') as f: f.write(selected)
assert selected.decode('ascii').splitlines()[17] == '# MHz S MA R 50'
source = dict(manufacturer='NXP Semiconductors', device='BFU530W',
              productURL='https://www.nxp.com/products/radio-frequency-rf/legacy-rf/legacy-rf-wideband-transistors/npn-wideband-silicon-rf-transistor:BFU530W',
              archiveURL='https://www.nxp.com/downloads/en/s-parameters/BFU530W_Spar.zip',
              officialListing=dict(description='BFU530W: S-parameters 40 MHz - 6 GHz', revision='1.0', date='2019-04-23'),
              retrievedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              archiveBytes=len(raw), archiveSHA256=sha(raw), entries=entries,
              selectedMember=MEMBER, selectedBytes=len(selected), selectedSHA256=sha(selected),
              selectedHeader=dict(format='MHz S MA R 50', nominalBias='3.3V / 1mA (filename)',
                                  measuredHeaderDate='2013-03-26 18:05:03',
                                  biasHeaderValues={'V_out':'3.3010','I_out':'0.9950','V_in':'0.7835','I_in':'0.0103'},
                                  preprocessing='manufacturer header says deembedded for feedlines and parallel'),
              priorManufacturer='Johanson Technology; Agilent E5071C is the instrument, not the DUT vendor',
              termsURL='https://www.nxp.com/pages/terms-of-use:TERMSOFUSE',
              termsObservation='Default published-content permission is limited to unmodified personal non-commercial use; other uses require consent; download software may have a separate license. No broader redistribution license was present in this ZIP.',
              copyrightScope='NXP original data are not the project MIT code; no endorsement or external adoption claimed',
              redistributionPermissionConfirmed=False, privateExcludedDirectory=str(PRIVATE),
              privateExcludedKinds=['source ZIP and duplicate HTTP response', 'selected original S2P', 'full-value CLI dumps and rewritten S2P'],
              actualDownload=dict(client='curl.exe default user agent; public official URL; no login',
                                  toolChunk='2e039b', httpStatus=200, exitCode=0, bytes=118380,
                                  headersPath=str(PRIVATE/'nxp-curl.headers.txt'),
                                  headersSHA256=sha((PRIVATE/'nxp-curl.headers.txt').read_bytes())),
              earlierAttempts=[dict(client='Python urllib', toolChunk='22668b', exitCode=1, result='HTTP404, zero saved bytes'),
                               dict(client='curl.exe', toolChunk='10c190', exitCode=1, result='local output-directory error before HTTP; no download')])
json_new(E/'SOURCE.json', source)
before = product_inputs()
json_new(E/'INPUTS-BEFORE.json', dict(moduleVersion='0.3.0', files=before,
         moon=str(MOON), moonSHA256=sha(MOON.read_bytes()), selectedInputSHA256=sha(selected)))
env = os.environ.copy()
env['MOON_HOME'] = str(MOON.parent.parent)
env['PATH'] = str(MOON.parent)+os.pathsep+env.get('PATH','')
command = [str(MOON),'build','--target','js','--release','--deny-warn']
start = time.perf_counter_ns()
with (E/'build.stdout.raw').open('xb') as stdout, (E/'build.stderr.raw').open('xb') as stderr:
    child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    code = child.wait(timeout=60)
terminal = dict(command=command, cwd=str(ROOT), pid=child.pid, exitCode=code,
                elapsedNs=time.perf_counter_ns()-start, environmentOverrides={'MOON_HOME':env['MOON_HOME'],'PATHPrefix':str(MOON.parent)},
                stdoutSHA256=sha((E/'build.stdout.raw').read_bytes()), stderrSHA256=sha((E/'build.stderr.raw').read_bytes()))
json_new(E/'build.terminal.json', terminal)
assert code == 0, terminal
after = product_inputs()
assert before == after, 'Unexpected product input change'
engine = ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
json_new(E/'BUILD.json', dict(status='built-current-unchanged-0.3.0-cli', terminal=terminal,
                            sourceFilesUnchanged=True, sourceInputCount=len(before),
                            enginePath=str(engine), engineSHA256=sha(engine.read_bytes()),
                            scope='one JS CLI build; no old tests, examples, old manufacturer inputs or full reference suite rerun'))
print(json.dumps(dict(buildExitCode=code, selectedMember=MEMBER, inputSHA256=sha(selected),
                      engineSHA256=sha(engine.read_bytes()), sourceInputs=len(before))))
