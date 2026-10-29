#!/usr/bin/env python3
"""Receive complete sampled NF reports with an independent rational oracle."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', required=True)
options = parser.parse_args()
evidence = Path(options.evidence).resolve()
assert not evidence.exists(), 'Preserve old evidence; choose a fresh path'
evidence.parent.mkdir(parents=True, exist_ok=True)
files = evidence.with_name(evidence.stem + '-cases')
files.mkdir(exist_ok=False)
calls, checks, inputs = [], [], {}


def check(label, condition):
    checks.append(label)
    if not condition:
        raise AssertionError(label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fresh(name, data):
    if isinstance(data, str):
        data = data.encode('ascii')
    path = files / name
    with path.open('xb') as stream:
        stream.write(data)
    inputs[str(path)] = sha(data)
    return path


def compare(label, actual, wanted):
    if isinstance(wanted, dict):
        check(label + ': full schema', isinstance(actual, dict) and set(actual) == set(wanted))
        for key in wanted:
            compare(label + '/' + key, actual[key], wanted[key])
    elif isinstance(wanted, list):
        check(label + ': full array', isinstance(actual, list) and len(actual) == len(wanted))
        for i, (a, b) in enumerate(zip(actual, wanted)):
            compare(label + f'/{i}', a, b)
    elif isinstance(wanted, (int, float)) and not isinstance(wanted, bool):
        check(label + ': finite', isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual))
        check(label + ': independent value', abs(actual - wanted) <= 2e-12 * max(1, abs(wanted)))
    else:
        check(label + ': exact condition', actual == wanted)


def call(label, source, query=None, code=0, output=None, command='noise-check', error=None):
    argv = ['node', 'tools/touchstone.mjs', command, str(source), json.dumps(query or {})]
    if output is not None:
        argv.append(str(output))
    existed = output is not None and output.exists()
    run = subprocess.run(argv, cwd=P, capture_output=True)
    stem = f'{len(calls)+1:02d}-{label}'
    receipt = {'label': label, 'argv': argv, 'exitCode': run.returncode, 'expectedExitCode': code}
    for stream in ['stdout', 'stderr']:
        data = getattr(run, stream)
        path = files / (stem + '.' + stream + '.txt')
        path.write_bytes(data)
        receipt[stream] = str(path.relative_to(evidence.parent))
        receipt[stream + 'SHA256'] = sha(data)
    calls.append(receipt)
    check(label + ': exit', run.returncode == code)
    if code == 2:
        check(label + ': no partial stdout', not run.stdout and bool(run.stderr))
        if error:
            check(label + ': explicit error', error in run.stderr.decode('utf-8'))
        if output is not None and not existed:
            check(label + ': no partial new file', not output.exists())
        return None
    check(label + ': no stderr', not run.stderr)
    if output is not None:
        check(label + ': actual saved report only', output.is_file() and not run.stdout)
        return output.read_bytes()
    return run.stdout


FREQUENCIES = [1000000, 2000000, 4000000, 5000000]
REFS = [75, 100]
INFO = ['synthetic noise acceptance run', 'source impedance is referred to noise R50']
NOISE = [{'frequency_hz': f, 'minimum_figure_db': 0, 'gamma_opt': {'re': 0, 'im': 0},
          'resistance_ohms': rn} for f, rn in [(1000000, 25), (5000000, 125)]]
# For this independent PSD model Fmin=1, Gamma_opt=0 and Znoise=50ohm.
# Zsource=100ohm gives Gamma=1/3, hence F=1+Rn/100. Interpolation of
# proportional endpoint covariances gives exact Rn25/50/100/125ohm.
FACTORS = [Fraction(5, 4), Fraction(3, 2), Fraction(2), Fraction(9, 4)]
DB = [10 * math.log10(float(x)) for x in FACTORS]
MAIN = {'start_hz': 2000000, 'end_hz': 4000000, 'maximum_db': 2,
        'source_mode': 'impedance', 'source_ohms': [100, 0]}
GAMMA = {**MAIN, 'source_mode': 'gamma', 'source': [1/3, 0]}
del GAMMA['source_ohms']


def wanted(query, db=None, noise_records=2):
    # Complete receiving contract from original coordinates and independent
    # analytic NF; no product output, inverse or library checker used.
    db = DB if db is None else db
    start, end, limit = [query[k] for k in ['start_hz', 'end_hz', 'maximum_db']]
    mode = query.get('source_mode', 'gamma')
    source = query['source_ohms'] if mode == 'impedance' else query.get('source', [0, 0])
    rows = [{'point': i, 'frequency_hz': f, 'figure_db': db[i], 'above_maximum': db[i] > limit,
             'status': 'fail' if db[i] > limit else 'pass'} for i, f in enumerate(FREQUENCIES) if start <= f <= end]
    failed = sum(row['above_maximum'] for row in rows)
    covered = FREQUENCIES[0] <= start and FREQUENCIES[-1] >= end
    return {'kind': 'noise_figure_band_report', 'scope': 'sampled_points_only', 'figure_units': 'dB',
        'status': 'fail' if failed else 'inconclusive' if not rows or not covered else 'pass',
        'start_hz': start, 'end_hz': end, 'maximum_db': limit, 'source_mode': mode,
        'source': {'re': source[0], 'im': source[1]}, 'source_units': 'ohm' if mode == 'impedance' else 'dimensionless',
        'network_reference_ohms': REFS, 'noise_reference_ohms': 50, 'noise_records': noise_records,
        'available_start_hz': FREQUENCIES[0], 'available_end_hz': FREQUENCIES[-1], 'range_covered': covered,
        'start_sampled': start in FREQUENCIES, 'end_sampled': end in FREQUENCIES,
        'sample_count': len(rows), 'failed_count': failed,
        'highest': max(rows, key=lambda x: x['figure_db']) if rows else None, 'samples': rows}


def receive(label, source, query, code, db=None, count=2, output=None):
    raw = call(label, source, query, code, output=output)
    compare(label + ': all report conditions/rows', json.loads(raw), wanted(query, db, count))
    return raw


source_path = P / 'examples/noise-limits.ts'
source_bytes = source_path.read_bytes()
source = fresh('actual-original-input-copy.ts', source_bytes)
check('original input exact tested copy', source.read_bytes() == source_bytes)
inspect = json.loads(call('original-conditions', source, command='inspect'))
compare('original document conditions', inspect, {'ports': 2, 'parameter': 'S', 'points': 4,
    'frequency_hz': FREQUENCIES, 'reference_ohms': REFS, 'noise_reference_ohms': 50,
    'noise': NOISE, 'mixed_mode_order': [], 'information': INFO})
receive('gamma-failing-band', source, GAMMA, 3)
saved = files / 'actual-impedance-report.json'
receive('physical-failing-band-save', source, MAIN, 3, output=saved)
compare('independent actual saved-file receiver', json.loads(saved.read_bytes()), wanted(MAIN))

packages = []
for backend in ['js', 'wasm-gc']:
    path = P / f'_build/ci/noise-check-example-{backend}.json'
    package = json.loads(path.read_bytes())
    check(backend + ': all public execution fields', set(package) == {'input_text', 'original', 'gamma_report', 'impedance_report'})
    check(backend + ': actual runtime original input', package['input_text'].encode('ascii') == source_bytes)
    original = {**inspect, 'values': [[{'re': v, 'im': 0} for v in [1/8, 1/16, 1/2, 1/4]] for _ in FREQUENCIES]}
    compare(backend + ': complete source matrix/conditions', package['original'], original)
    compare(backend + ': full gamma report', package['gamma_report'], wanted(GAMMA))
    compare(backend + ': full physical report', package['impedance_report'], wanted(MAIN))
    actual_report = fresh('actual-public-' + backend + '-report.json', json.dumps(package['impedance_report'], indent=2) + '\n')
    compare(backend + ': actual exported report receiver', json.loads(actual_report.read_bytes()), wanted(MAIN))
    packages.append({'backend': backend, 'actualOutput': str(path), 'outputSHA256': sha(path.read_bytes()),
                     'actualProducedReport': str(actual_report), 'producedReportSHA256': sha(actual_report.read_bytes())})

for label, query, code in [
    ('physical-pass', {**MAIN, 'maximum_db': 4}, 0),
    ('gamma-pass', {**GAMMA, 'maximum_db': 4}, 0),
    ('empty-within-extent', {**MAIN, 'start_hz': 2500000, 'end_hz': 3500000, 'maximum_db': 4}, 4),
    ('uncovered-no-failure', {**MAIN, 'start_hz': 0, 'end_hz': 2000000, 'maximum_db': 4}, 4),
    ('known-failure-wins', {**MAIN, 'start_hz': 0}, 3),
    ('nonaligned-original-points', {**MAIN, 'start_hz': 1500000, 'end_hz': 4500000, 'maximum_db': 4}, 0),
    ('singleton-equal-edges', {**MAIN, 'end_hz': 2000000}, 0),
]:
    receive(label, source, query, code)
matched = {'start_hz': 1000000, 'end_hz': 5000000, 'maximum_db': 0}
receive('default-matched-exact-zero-equality-first-tie', source, matched, 0, [0]*4)
receive('negative-limit-valid-failure', source, {**matched, 'maximum_db': -1}, 3, [0]*4)

text = source_bytes.decode('ascii')
constant_text = text.replace('[Number of Noise Frequencies] 2', '[Number of Noise Frequencies] 1').split('[Noise Data]')[0] + '[Noise Data]\n0 0 0 0 50\n[End]\n'
constant = fresh('single-constant-noise.ts', constant_text)
receive('constant-record-does-not-extrapolate', constant, {**MAIN, 'start_hz': 1000000, 'end_hz': 5000000}, 0, [10*math.log10(1.5)]*4, 1)
zero = fresh('explicit-zero-noise.ts', constant_text.replace('0 0 0 0 50', '0 0 0 0 0'))
receive('explicit-zero-noise-not-missing', zero, matched, 0, [0]*4, 1)

for label, command, query, filename in [
    ('old-gamma-full-byte-control', 'noise', {'source': [1/3, 0]}, 'gamma-before.json'),
    ('old-impedance-full-byte-control', 'noise', {'source_mode': 'impedance', 'source_ohms': [100, 0]}, 'impedance-before.json'),
    ('old-normalize-full-byte-control', 'normalize', {}, 'normalize-before.ts'),
]:
    data = call(label, source, query, command=command)
    check(label + ': full existing output bytes', data == (P / 'tools/fixtures/noise-check' / filename).read_bytes())

missing_text = text.replace('[Number of Noise Frequencies] 2\n', '').split('[Noise Data]')[0] + '[End]\n'
missing = fresh('no-actual-noise.ts', missing_text)
call('old-missing-noise-parses', missing, command='inspect')
call('missing-noise-rejected', missing, MAIN, 2, files / 'no-missing.json', error='requires two-port noise data')
mixed = fresh('mixed-actual-noise.ts', text.replace('[Reference] 75 100', '[Reference] 50 50\n[Mixed-Mode Order] D1,2 C1,2'))
call('old-mixed-noisy-parses', mixed, command='inspect')
call('mixed-report-rejected', mixed, MAIN, 2, files / 'no-mixed.json', error='single-ended document')
nonphysical = fresh('nonphysical-noise.ts', constant_text.replace('0 0 0 0 50', '0 20 0 0 1'))
call('nonphysical-covariance-old-rejection', nonphysical, {'source_mode': 'impedance', 'source_ohms': [100, 0]}, 2, command='noise')
call('nonphysical-covariance-new-rejection', nonphysical, MAIN, 2, files / 'no-nonphysical.json')
uncovered = fresh('noise-grid-not-covering-network.ts', text.replace('[Noise Data]\n1 0 0 0 25\n5 0 0 0 125', '[Noise Data]\n2 0 0 0 50\n4 0 0 0 100'))
call('old-uncovered-noise-parses', uncovered, command='inspect')
call('full-grid-outside-band-still-errors', uncovered, MAIN, 2, files / 'no-extrapolate.json', error='outside measured range')
call('old-full-grid-error-retained', uncovered, {'source_mode': 'impedance', 'source_ohms': [100, 0]}, 2, command='noise', error='outside measured range')

invalid = [
    ('missing-maximum', {k: v for k, v in MAIN.items() if k != 'maximum_db'}, None),
    ('wrong-maximum-type', {**MAIN, 'maximum_db': '2'}, None),
    ('negative-hz', {**MAIN, 'start_hz': -1}, None),
    ('reversed-band', {**MAIN, 'start_hz': 5000000}, None),
    ('active-gamma-source', {**GAMMA, 'source': [1, 0]}, None),
    ('nonpositive-resistance', {**MAIN, 'source_ohms': [0, 1]}, None),
    ('missing-physical-source', {k: v for k, v in MAIN.items() if k != 'source_ohms'}, None),
    ('opposite-mode-ohms', {**GAMMA, 'source_ohms': [100, 0]}, 'unknown noise check option'),
    ('opposite-mode-gamma', {**MAIN, 'source': [0, 0]}, 'unknown noise check option'),
    ('unknown-mode', {**MAIN, 'source_mode': 'voltage'}, 'unknown noise check source_mode'),
    ('fixture-key-never-read', {**MAIN, 'left_file': 'never-read-third-file.ts'}, 'unknown noise check option'),
    ('unneeded-pairs', {**MAIN, 'pairs': [[0, 1]]}, 'unknown noise check option'),
    ('caller-port-conflict', {**MAIN, 'ports': 3}, 'conflicts with header'),
    ('missing-start', {k: v for k, v in MAIN.items() if k != 'start_hz'}, None),
]
for i, (label, query, error) in enumerate(invalid):
    call(label, source, query, 2, files / f'no-invalid-{i}.json', error=error)
occupied = fresh('occupied-report.json', 'preserve occupied report\n')
call('occupied-output', source, MAIN, 2, occupied, error='EEXIST')
call('same-path-output', source, MAIN, 2, source, error='EEXIST')
call('missing-output-parent', source, MAIN, 2, files / 'absent/out.json', error='ENOENT')
for path, digest in inputs.items():
    check('preserved input/actual-copy:' + Path(path).name, sha(Path(path).read_bytes()) == digest)

receipt = {'status': 'passed', 'actualCLIProcesses': len(calls), 'receivingChecks': len(checks), 'checkNames': checks,
    'oracle': 'Independent exact rational factors5/4,3/2,2,9/4 from original PSD noise parameters and100ohm source vs50ohm noise reference; all original indices/conditions/statuses/rows consumed',
    'newMathOrProductionBugClaimed': False, 'packageExecutionsConsumed': packages,
    'actualTestInputCopies': [{'originalWorkingPath': str(source_path), 'originalWorkingSHA256': sha(source_bytes),
        'actualTestCopy': str(source), 'actualTestCopySHA256': sha(source.read_bytes()), 'byteIdentical': source.read_bytes() == source_bytes}],
    'sourceWorkingBytesSHA256': {name: sha((P/name).read_bytes()) for name in ['noise_band.mbt','noise_band_test.mbt','cmd/bridge/main.mbt','tools/touchstone.mjs','examples/noise_check/main.mbt','tools/verify-noise-check.py']},
    'actualBridge': {'path': str(P/'_build/js/release/build/cmd/bridge/bridge.js'), 'sha256': sha((P/'_build/js/release/build/cmd/bridge/bridge.js').read_bytes())},
    'inputSHA256': inputs, 'calls': calls, 'externalAdoptionClaimed': False, 'nativeRuntimeClaimed': False}
evidence.write_text(json.dumps(receipt, indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status': 'passed', 'actualCLIProcesses': len(calls), 'receivingChecks': len(checks), 'evidence': str(evidence)}))
