#!/usr/bin/env python3
"""Independent finite-SI-seconds package and arbitrary-file receivers."""
import argparse
from decimal import Decimal, localcontext
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
assert not evidence.exists(), 'Use fresh evidence; preserve previous attempts'
evidence.parent.mkdir(parents=True, exist_ok=True)
files = evidence.with_name(evidence.stem + '-cases')
files.mkdir(exist_ok=False)
checks, calls, inputs = [], [], {}
TINY = float.fromhex('0x0.0000000000001p-1022')
PI = Decimal('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')
with localcontext() as context:
    context.prec = 100
    y = Decimal.from_float(1e-15)
    angle = sum(((-1) ** k * y ** (2 * k + 1) / (2 * k + 1) for k in range(4)), Decimal(0))
    magnitude = float(angle / (2 * PI * Decimal.from_float(TINY)))


def check(label, condition):
    checks.append(label)
    if not condition:
        raise AssertionError(label)


def close(label, value, expected):
    check(label + ': finite', isinstance(value, (float, int)) and math.isfinite(value))
    check(label + ': independent seconds', value == 0 if expected == 0 else abs(value / expected - 1) < 5e-13)


def fresh(name, text):
    path = files / name
    with path.open('x', encoding='ascii', newline='') as stream:
        stream.write(text)
    inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def call(label, command, source, query=None, code=0, output=None, error=None):
    request = {'input': 0, 'output': 1, **(query or {})}
    argv = ['node', 'tools/touchstone.mjs', command, str(source), json.dumps(request)]
    if output is not None:
        argv.append(str(output))
    existed = output is not None and output.exists()
    result = subprocess.run(argv, cwd=P, capture_output=True)
    stem = f'{len(calls) + 1:02d}-{label}'
    for stream in ['stdout', 'stderr']:
        (files / (stem + '.' + stream + '.txt')).write_bytes(getattr(result, stream))
    calls.append({'label': label, 'argv': argv, 'exitCode': result.returncode, 'expectedExitCode': code,
                  **{stream: str((files / (stem + '.' + stream + '.txt')).relative_to(evidence.parent)) for stream in ['stdout', 'stderr']},
                  **{stream + 'SHA256': hashlib.sha256(getattr(result, stream)).hexdigest() for stream in ['stdout', 'stderr']}})
    check(label + ': exit', result.returncode == code)
    if code == 2:
        check(label + ': explicit error/no stdout', not result.stdout and bool(result.stderr))
        if error:
            check(label + ': error reason', error in result.stderr.decode('utf-8'))
        if output is not None and not existed:
            check(label + ': no partial output', not output.exists())
        return None
    check(label + ': no stderr', not result.stderr)
    if output is not None:
        check(label + ': saved report only', not result.stdout and output.exists())
        return json.loads(output.read_bytes())
    return json.loads(result.stdout)


def full_delay(label, values, expected):
    check(label + ': complete array', isinstance(values, list) and len(values) == len(expected))
    for i, wanted in enumerate(expected):
        close(label + ':' + str(i), values[i], wanted)


def full_report(label, value, frequencies, expected, query, refs=None):
    required = {'kind', 'scope', 'estimator', 'status', 'start_hz', 'end_hz', 'input', 'output',
                'reference_ohms', 'minimum_seconds', 'maximum_seconds', 'sample_count',
                'failed_count', 'below_minimum_count', 'above_maximum_count', 'range_covered',
                'start_sampled', 'end_sampled', 'lowest', 'highest', 'samples'}
    check(label + ': complete schema', set(value) == required)
    start, end = query['start_hz'], query['end_hz']
    minimum, maximum = query.get('minimum_seconds'), query.get('maximum_seconds')
    points = [i for i, f in enumerate(frequencies) if start <= f <= end]
    covered = frequencies[0] <= start and frequencies[-1] >= end
    below = [i for i in points if minimum is not None and expected[i] < minimum]
    above = [i for i in points if maximum is not None and expected[i] > maximum]
    status = 'fail' if below or above else 'inconclusive' if not points or not covered else 'pass'
    check(label + ': identity and references', value['kind'] == 'group_delay_band_report'
          and value['scope'] == 'sampled_points_only' and value['estimator'] == 'endpoint_or_centered_secant'
          and value['input'] == 0 and value['output'] == 1 and value['reference_ohms'] == (refs or [50, 75]))
    check(label + ': full query', value['start_hz'] == start and value['end_hz'] == end
          and value['minimum_seconds'] == minimum and value['maximum_seconds'] == maximum)
    check(label + ': outcome/counts', value['status'] == status and value['sample_count'] == len(points)
          and value['failed_count'] == len(below) + len(above)
          and value['below_minimum_count'] == len(below) and value['above_maximum_count'] == len(above))
    check(label + ': coverage/endpoints', value['range_covered'] == covered
          and value['start_sampled'] == (start in frequencies) and value['end_sampled'] == (end in frequencies))
    check(label + ': all original samples', len(value['samples']) == len(points))
    for row, i in zip(value['samples'], points):
        check(label + f':{i}: complete row', set(row) == {'point', 'frequency_hz', 'delay_seconds',
              'aperture_start_hz', 'aperture_end_hz', 'below_minimum', 'above_maximum', 'status'})
        check(label + f':{i}: original point/aperture', row['point'] == i and row['frequency_hz'] == frequencies[i]
              and row['aperture_start_hz'] == frequencies[max(0, i - 1)]
              and row['aperture_end_hz'] == frequencies[min(len(frequencies) - 1, i + 1)])
        close(label + f':{i}', row['delay_seconds'], expected[i])
        check(label + f':{i}: exact disposition', row['below_minimum'] == (i in below)
              and row['above_maximum'] == (i in above)
              and row['status'] == ('fail' if i in below or i in above else 'pass'))
    if points:
        for name, point in [('lowest', min(points, key=lambda i: expected[i])),
                            ('highest', max(points, key=lambda i: expected[i]))]:
            check(label + ':' + name + ': independently located first witness',
                  value[name] == value['samples'][points.index(point)])
    else:
        check(label + ': no invented extrema', value['lowest'] is None and value['highest'] is None)


def source_text(frequencies, imaginary, version='2.1', zero_last=False):
    header = f'[Version] {version}\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Reference] 50 75\n[Number of Frequencies] {len(frequencies)}\n[Network Data]\n'
    rows = []
    for i, (f, im) in enumerate(zip(frequencies, imaginary)):
        real = 0 if zero_last and i == len(frequencies) - 1 else 1
        rows.append(f'{f} 0 0 0 0 {real} {im} 0 0\n')
    return header + ''.join(rows) + '[End]\n'


cases = [
    ('negative-two-point', [0, TINY], [0, 1e-15], [-magnitude, -magnitude], -5e307, 0),
    ('positive-two-point', [0, TINY], [0, -1e-15], [magnitude, magnitude], 0, 5e307),
    ('nonuniform-return', [0, TINY, 3 * TINY], [0, 1e-15, 0], [-magnitude, 0, magnitude / 2], -5e307, 2e307),
]
packages = []
for backend in ['js', 'wasm-gc']:
    path = P / f'_build/ci/delay-finite-example-{backend}.json'
    data = json.loads(path.read_bytes())
    check(backend + ': public cases schema', set(data) == {'cases'} and len(data['cases']) == 3)
    for row, (name, frequencies, imaginary, expected, minimum, maximum) in zip(data['cases'], cases):
        label = backend + '-' + name
        check(label + ': complete package result', set(row) == {'name', 'input_text', 'network', 'delay_seconds', 'minimum_seconds', 'maximum_seconds', 'report'})
        check(label + ': original name/bounds', row['name'] == name and row['minimum_seconds'] == minimum and row['maximum_seconds'] == maximum)
        # Check all source coordinates independently, not just the phase trace.
        net = row['network']
        check(label + ': network schema', set(net) == {'ports', 'parameter', 'frequency_hz', 'reference_ohms', 'values'})
        check(label + ': network conditions', net['ports'] == 2 and net['parameter'] == 'S'
              and net['frequency_hz'] == frequencies and net['reference_ohms'] == [50, 75])
        check(label + ': source input records', len(net['values']) == len(frequencies))
        for matrix, im in zip(net['values'], imaginary):
            check(label + ': all original matrix coordinates', matrix == [{'re': 0, 'im': 0}, {'re': 0, 'im': 0}, {'re': 1, 'im': im}, {'re': 0, 'im': 0}])
        full_delay(label, row['delay_seconds'], expected)
        query = {'start_hz': frequencies[0], 'end_hz': frequencies[-1], 'minimum_seconds': minimum, 'maximum_seconds': maximum}
        full_report(label, row['report'], frequencies, expected, query)
        # Consume actual public-package file bytes after independently checking
        # all their decoded original input coordinates above.
        input_file = fresh(label + '.ts', row['input_text'])
        full_delay(label + '-file', call(label + '-delay', 'delay', input_file), expected)
        saved = files / (label + '-report.json')
        full_report(label + '-saved', call(label + '-check', 'delay-check', input_file, query, output=saved), frequencies, expected, query)
    packages.append({'backend': backend, 'output': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

negative = fresh('fresh-legacy.s2p', '# Hz S RI R 50 75\n0 0 0 1 0 0 0 0 0\n5e-324 0 0 1 1e-15 0 0 0 0\n')
two = [0, TINY]
for label, query, code in [
    ('negative-pass', {'start_hz': 0, 'end_hz': TINY, 'minimum_seconds': -5e307, 'maximum_seconds': 0}, 0),
    ('negative-fail', {'start_hz': 0, 'end_hz': TINY, 'minimum_seconds': 0}, 3),
]:
    saved = files / (label + '.json')
    full_report(label, call(label, 'delay-check', negative, query, code, saved), two, [-magnitude] * 2, query)
positive = fresh('fresh-positive-2.0.ts', source_text(two, [0, -1e-15], version='2.0'))
full_delay('positive-file', call('positive-file', 'delay', positive), [magnitude] * 2)
query = {'start_hz': 0, 'end_hz': TINY, 'maximum_seconds': 1e307}
full_report('positive-fail', call('positive-fail', 'delay-check', positive, query, 3), two, [magnitude] * 2, query)
frequencies = [0, TINY, 3 * TINY]
expected = [-magnitude, 0, magnitude / 2]
nonuniform = fresh('fresh-nonuniform.ts', source_text(frequencies, [0, 1e-15, 0]))
for label, query, code in [
    ('middle-full-aperture', {'start_hz': TINY, 'end_hz': TINY, 'minimum_seconds': 0, 'maximum_seconds': 0}, 0),
    ('first-only-fail', {'start_hz': 0, 'end_hz': 0, 'minimum_seconds': 0}, 3),
    ('uncovered-fail-priority', {'start_hz': 0, 'end_hz': 4*TINY, 'minimum_seconds': 0}, 3),
    ('uncovered-inconclusive', {'start_hz': 0, 'end_hz': 4*TINY, 'minimum_seconds': -5e307, 'maximum_seconds': 2e307}, 4),
    ('empty-covered', {'start_hz': 2*TINY, 'end_hz': 2*TINY, 'minimum_seconds': 0}, 4),
]:
    full_report(label, call(label, 'delay-check', nonuniform, query, code), frequencies, expected, query)
zero = fresh('fresh-zero-delay.ts', source_text(two, [0, 0]))
query = {'start_hz': 0, 'end_hz': TINY, 'minimum_seconds': 0, 'maximum_seconds': 0}
full_report('exact-zero', call('exact-zero', 'delay-check', zero, query), two, [0, 0], query)

golden = json.loads((P / 'tools/fixtures/delay-finite-seconds/ordinary-before.json').read_bytes())
ordinary = fresh('ordinary.s2p', golden['input_text'])
delay_value = call('ordinary-delay', 'delay', ordinary)
full_delay('ordinary-delay', delay_value, [-2.5e-7] * 2)
check('ordinary entire delay golden', delay_value == json.loads(golden['delay_stdout']))
query = {'start_hz': 1e6, 'end_hz': 2e6, 'maximum_seconds': 0}
report_value = call('ordinary-report', 'delay-check', ordinary, query)
full_report('ordinary-report', report_value, [1e6, 2e6], [-2.5e-7] * 2, query, refs=[50, 50])
check('ordinary entire report golden', report_value == json.loads(golden['report_stdout']))
# Also preserve original JSON output bytes on the unchanged finite path.
for label, field in [('ordinary-delay', 'delay_stdout'), ('ordinary-report', 'report_stdout')]:
    record = next(c for c in calls if c['label'] == label)
    check(label + ': golden output bytes', (evidence.parent / record['stdout']).read_bytes() == golden[field].encode('ascii'))

overflow = fresh('final-overflow.ts', source_text(two, [0, 1e-14]))
for command in ['delay', 'delay-check']:
    call('reject-final-' + command, command, overflow, query={'start_hz': 0, 'end_hz': TINY, 'minimum_seconds': 0}, code=2, output=files / ('no-' + command + '.json'), error='group delay overflow')
outside_zero = fresh('outside-zero.ts', source_text(frequencies, [0, 0, 0], zero_last=True))
call('reject-outside-zero', 'delay-check', outside_zero, {'start_hz': 0, 'end_hz': 0, 'minimum_seconds': 0}, 2, files / 'no-zero.json', 'zero transmission')
one = fresh('one-point.ts', source_text([0], [0]))
call('reject-one-point', 'delay-check', one, {'start_hz': 0, 'end_hz': 0, 'minimum_seconds': 0}, 2, files / 'no-one.json', 'at least two frequencies')
call('reject-port', 'delay', negative, {'output': 2}, 2, files / 'no-port.json', 'port index outside range')
occupied = fresh('occupied.json', 'preserve occupied output\n')
call('exclusive-output', 'delay-check', negative, {'start_hz': 0, 'end_hz': TINY, 'minimum_seconds': -5e307}, 2, occupied, 'EEXIST')
for path, digest in inputs.items():
    check('preserved input/occupied bytes:' + Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest)

receipt = {'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': len(checks),
           'checkNames': checks, 'oracle': '100-digit Decimal exact binary64 inputs, independent atan series/pi and hand-derived endpoint/centered secants; no product-generated numerical expectation',
           'independentMagnitudeSeconds': magnitude, 'packageExecutionsConsumed': packages,
           'sourceWorkingBytesSHA256': {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in ['analysis.mbt', 'group_delay_scale_test.mbt', 'examples/delay_finite_seconds/main.mbt', 'tools/verify-delay-finite-seconds.py']},
           'actualBridge': {'path': str(P / '_build/js/release/build/cmd/bridge/bridge.js'), 'sha256': hashlib.sha256((P / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()).hexdigest()},
           'calls': calls, 'inputSHA256': inputs, 'externalAdoptionClaimed': False,
           'wholeBinary64TheoremClaimed': False, 'nativeRuntimeClaimed': False}
evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': len(checks), 'evidence': str(evidence)}))
